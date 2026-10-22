import logging
import re
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.config import settings
from app.schemas.evidence_schema import EvidenceCardResponse, KnowledgeSourceResponse
from app.services.llm_service import generate_structured_response

logger = logging.getLogger(__name__)

DOMAIN_MAP = {
    "phap_ly": "Hành chính – Pháp lý",
    "cong_viec": "Học tập – Công việc",
    "giao_tiep": "Giao tiếp – Văn hoá ứng xử",
    "nha_o": "Nhà ở – Tiện ích",
    "tai_chinh": "Tài chính – Ngân hàng",
    "y_te": "Y tế – Bảo hiểm",
    "giao_thong": "Giao thông – Đi lại",
    "doi_song": "Đời sống hằng ngày – Ẩm thực",
    "cong_dong": "Cộng đồng – Mạng lưới hỗ trợ"
}

COUNTRY_MAP = {
    "JP": "Nhật Bản",
    "KR": "Hàn Quốc",
    "AU": "Australia"
}

_transformed_engine = None

def get_transformed_engine():
    global _transformed_engine
    if _transformed_engine is None:
        _transformed_engine = create_engine(
            settings.TRANSFORMED_DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5
        )
    return _transformed_engine


# =====================================================================
# BỘ LỌC Ý ĐỊNH HỘI THOẠI CƠ BẢN (CONVERSATIONAL GUARDRAIL & GREETINGS)
# =====================================================================
def detect_conversational_intent(query: str, country: str = "JP") -> Optional[Dict[str, Any]]:
    """
    Nhận diện các ý định hội thoại đời thường (Small-talk & Greeting):
    - Chào hỏi: hello, hi, xin chào, alo, good morning...
    - Hỏi danh tính / Chức năng: bạn là ai, bot là ai, dci là gì, who are you...
    - Cảm ơn / Tạm biệt: cảm ơn, thank you, tạm biệt, bye...
    Chỉ kích hoạt khi câu ngắn (dưới 7 từ) để không nhầm lẫn với câu hỏi nghiệp vụ.
    """
    q_clean = query.strip().lower()
    q_norm = re.sub(r'[?!.,;:\-_]', ' ', q_clean).strip()
    words = q_norm.split()

    if len(words) > 7:
        return None

    country_name = COUNTRY_MAP.get(country, "Nhật Bản")

    # 1. Chào hỏi (Greeting: <= 4 từ)
    greeting_triggers = ["xin chào", "chào bạn", "chào bot", "chào ad", "chào mọi người", "chào nha", "chào ạ", "hello", "hi", "hey", "alo", "good morning", "hế lô", "hé lô"]
    if len(words) <= 4 and (q_norm in ["chào", "hi", "hello", "alo"] or any(g in q_norm for g in greeting_triggers)):
        return {
            "success": True,
            "response_type": "GREETING",
            "direct_message": (
                f"Xin chào bạn! Tôi là DCI Copilot – Trợ lý hỗ trợ thích nghi văn hóa số tại {country_name}. "
                "Tôi có thể giúp bạn giải đáp các tình huống ứng xử, giao tiếp, nhà ở, việc làm hoặc quy chuẩn thực tế. "
                "Hôm nay bạn cần hỗ trợ về chủ đề gì?"
            )
        }

    # 2. Hỏi danh tính / Chức năng (Identity & Capabilities)
    identity_triggers = ["bạn là ai", "bot là ai", "mày là ai", "who are you", "dci là gì", "bạn tên gì", "tên bạn là gì", "bạn có thể làm gì", "chức năng của bạn", "hướng dẫn sử dụng", "bạn giúp được gì"]
    if any(idt in q_norm for idt in identity_triggers):
        return {
            "success": True,
            "response_type": "IDENTITY",
            "direct_message": (
                "Tôi là DCI Copilot, trợ lý số thuộc đề án 'Phiên Dịch Văn Hóa Số' (Asteria - AISC'26). "
                "Nhiệm vụ của tôi là hỗ trợ người Việt Nam hòa nhập an toàn tại Nhật Bản, Hàn Quốc và Australia. "
                "Tôi có thể giúp bạn giải đáp các quy chuẩn văn hóa, cách xử lý tình huống phát sinh và các kinh nghiệm thực tế đã được đối soát chính thống."
            )
        }

    # 3. Lời cảm ơn (Gratitude: <= 5 từ)
    gratitude_triggers = ["cảm ơn", "cám ơn", "thank you", "thanks", "cam on"]
    if len(words) <= 5 and any(gr in q_norm for gr in gratitude_triggers):
        return {
            "success": True,
            "response_type": "GREETING",
            "direct_message": (
                "Rất vui được hỗ trợ bạn! Nếu bạn gặp bất kỳ thắc mắc hay tình huống văn hóa nào tại nước sở tại, "
                "đừng ngần ngại hỏi tôi nhé. Chúc bạn có những trải nghiệm thật an toàn và thuận lợi!"
            )
        }

    # 4. Tạm biệt (Farewell: <= 4 từ)
    farewell_triggers = ["tạm biệt", "bye", "goodbye", "tam biet", "hẹn gặp lại"]
    if len(words) <= 4 and any(fw in q_norm for fw in farewell_triggers):
        return {
            "success": True,
            "response_type": "GREETING",
            "direct_message": (
                "Tạm biệt bạn! Chúc bạn luôn có những trải nghiệm học tập và sinh sống an toàn, thành công."
            )
        }

    return None


# =====================================================================
# HÀM TRUY VẤN KHO RAG POSTGRESQL TRANSFORMED (MULTILINGUAL-E5-SMALL)
# =====================================================================
async def search_rag_knowledge(
    query: str,
    country: str,
    limit: int = 3,
    source_kind: Optional[str] = None
) -> Dict[str, Any]:
    """
    Truy vấn kho RAG mới (multilingual-e5-small, 384 dimensions):
    1. Gọi Embedding Service lấy vector và profile_id
    2. Truy vấn view knowledge.current_rag_chunks kết hợp knowledge.rag_embeddings
    3. Lọc country_code, loại trùng theo content_hash, ưu tiên EXTERNAL
    """
    query_clean = query.strip()
    country_code = country.strip().upper()

    if country_code not in {"JP", "KR", "AU"}:
        raise ValueError("Quốc gia chỉ hỗ trợ JP, KR hoặc AU")

    # 1. Gọi dịch vụ sinh vector (E5 small 384 chiều)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.EMBEDDING_SERVICE_URL}/embed",
            json={"texts": [query_clean], "kind": "query"}
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding service trả về mã lỗi {resp.status_code}: {resp.text}")
        embed_data = resp.json()

    if embed_data.get("dimension") != 384 or not embed_data.get("vectors") or not embed_data.get("profile_id"):
        raise ValueError("Phản hồi embedding không hợp lệ")

    vector = embed_data["vectors"][0]
    profile_id = embed_data["profile_id"]
    vec_literal = "[" + ",".join(str(float(x)) for x in vector) + "]"

    # 2. Truy vấn database aisc_data
    engine = get_transformed_engine()
    sql = text("""
        WITH candidates AS (
            SELECT
                c.chunk_id,
                c.document_id,
                c.country_code,
                c.source_kind,
                c.source_ref,
                c.title,
                c.content,
                COALESCE(
                    c.metadata->>'resolved_url',
                    c.metadata->>'source_url'
                ) AS source_url,
                e.embedding <=> cast(:vector as vector) AS distance,
                ROW_NUMBER() OVER (
                    PARTITION BY c.content_hash
                    ORDER BY
                        CASE
                            WHEN c.source_kind = 'EXTERNAL' THEN 0
                            ELSE 1
                        END,
                        c.document_id,
                        c.chunk_id
                ) AS duplicate_rank
            FROM knowledge.current_rag_chunks c
            JOIN knowledge.rag_embeddings e
              ON e.chunk_id = c.chunk_id
             AND e.content_hash = c.content_hash
            WHERE c.country_code = :country
              AND e.profile_id = :profile_id
              AND (:source_kind IS NULL OR c.source_kind = :source_kind)
        )
        SELECT
            chunk_id,
            document_id,
            country_code,
            source_kind,
            source_ref,
            title,
            content,
            source_url,
            1 - distance AS similarity
        FROM candidates
        WHERE duplicate_rank = 1
        ORDER BY distance, chunk_id
        LIMIT :limit;
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "vector": vec_literal,
                "country": country_code,
                "profile_id": profile_id,
                "source_kind": source_kind,
                "limit": limit
            }
        ).fetchall()

    matches = [
        {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "country_code": r.country_code,
            "source_kind": r.source_kind,
            "source_ref": r.source_ref,
            "title": r.title,
            "content": r.content,
            "source_url": r.source_url,
            "similarity": float(r.similarity)
        }
        for r in rows
    ]

    return {
        "query": query_clean,
        "country_code": country_code,
        "profile_id": profile_id,
        "matches": matches
    }


# =====================================================================
# QUY TRÌNH DYNAMIC HYBRID RAG TRÊN POSTGRESQL (PRODUCTION GRADE)
# =====================================================================
async def execute_rag_pipeline(
    db: Session,
    query: str,
    country: str = "JP",
    purpose: str = "DU_HOC",
    stage: str = "PREPARING"
) -> Dict[str, Any]:
    """
    Thực thi quy trình RAG chuẩn mực:
    1. Kiểm tra Guardrail hội thoại cơ bản (chào hỏi, cảm ơn, danh tính)
    2. Kiểm tra bộ lọc quốc gia nghiêm ngặt (JP, KR, AU)
    3. Truy vấn kho RAG mới (multilingual-e5-small + pgvector trên aisc_data)
    4. Kiểm soát ngưỡng tin cậy (CONFIDENCE_THRESHOLD):
       Tự động từ chối nếu không đủ bằng chứng đối soát trong hệ thống.
    5. Gọi LLM sinh câu trả lời có trích dẫn nguồn rõ ràng.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "success": False,
            "response_type": "OUT_OF_SCOPE",
            "refusal_message": "Vui lòng nhập câu hỏi để hệ thống hỗ trợ bạn."
        }

    # Chuẩn hóa quốc gia (mặc định JP nếu không hợp lệ)
    norm_country = country.strip().upper() if country else "JP"
    if norm_country not in {"JP", "KR", "AU"}:
        norm_country = "JP"
    country_name = COUNTRY_MAP.get(norm_country, "nước sở tại")

    # 1. Kiểm tra ý định hội thoại cơ bản (Chào hỏi / Cảm ơn / Danh tính)
    smalltalk_response = detect_conversational_intent(clean_query, norm_country)
    if smalltalk_response:
        return smalltalk_response

    # 2. Truy vấn kho RAG
    try:
        rag_search_result = await search_rag_knowledge(
            query=clean_query,
            country=norm_country,
            limit=3
        )
        matches = rag_search_result.get("matches", [])
    except Exception as e:
        logger.error(f"Lỗi khi truy vấn RAG Knowledge: {e}")
        matches = []

    # 3. Kiểm soát ngưỡng an toàn toán học (Chống suy diễn ảo giác)
    best_match = matches[0] if matches else None
    similarity_score = best_match["similarity"] if best_match else 0.0

    # Nếu không có bằng chứng hoặc độ tương đồng thấp hơn ngưỡng cho phép -> Báo ngoài phạm vi
    if not best_match or similarity_score < settings.CONFIDENCE_THRESHOLD:
        logger.info(
            f"RAG Refusal triggered: query='{clean_query}', country='{norm_country}', "
            f"best_score={similarity_score:.4f}, threshold={settings.CONFIDENCE_THRESHOLD}"
        )
        return {
            "success": False,
            "response_type": "OUT_OF_SCOPE",
            "refusal_message": (
                f"Câu trả lời cho vấn đề này hiện không thuộc phạm vi thông tin và quy chuẩn văn hóa mà hệ thống DCI cung cấp tại {country_name}. "
                "Bạn có thể đặt câu hỏi về các chủ đề văn hóa ứng xử, giao tiếp, nhà ở, lao động hoặc phép lịch sự thường ngày (Ví dụ: quy chuẩn cúi chào, xưng hô, ăn uống cùng người lớn tuổi, văn hóa tiền tip, v.v.) để tôi hỗ trợ bạn tốt nhất nhé!"
            )
        }

    # 4. Chuẩn bị Evidence Card tương thích để gửi cho LLM và UI
    is_external = best_match["source_kind"] == "EXTERNAL"
    org_name = (
        "JNTO (Cơ quan Xúc tiến Du lịch Nhật Bản)" if norm_country == "JP"
        else ("Cultural Atlas (Mosaica)" if is_external else "Cộng đồng Người Việt tại " + country_name)
    )
    doc_url = best_match.get("source_url") or "#"
    card_id = f"RAG-{best_match['chunk_id'][:12]}" if is_external else f"COM-{best_match['source_ref']}"

    card_dict = {
        "card_id": card_id,
        "source_id": best_match["source_ref"],
        "country_code": norm_country,
        "country_name": country_name,
        "domain_id": "giao_tiep",
        "domain_name": "Giao tiếp – Văn hoá ứng xử",
        "title": best_match["title"],
        "context": f"Quy chuẩn ứng xử và phép lịch sự tại {country_name}",
        "verified_content": best_match["content"],
        "safe_action": "",
        "donots": "",
        "reliability_score": int(round(similarity_score * 100)),
        "confidence_level": "Rất cao (Nguồn chính thống)" if is_external else "Đã xác minh (Cộng đồng)",
        "status": "APPROVED",
        "organization_name": org_name,
        "source_url": doc_url,
        "verified_date": None,
        "source": KnowledgeSourceResponse(
            source_id=best_match["source_ref"],
            country_code=norm_country,
            organization_name=org_name,
            source_type="EXTERNAL_OFFICIAL" if is_external else "COMMUNITY_APPROVED",
            document_title=best_match["title"],
            document_url=best_match.get("source_url"),
            reliability_score=int(round(similarity_score * 100))
        )
    }

    # 5. Sinh câu trả lời có cấu trúc thông qua LLM (Grounded Output)
    llm_output = await generate_structured_response(
        query=clean_query,
        evidence_card=card_dict,
        country=norm_country,
        matches=matches
    )

    card_dict["safe_action"] = llm_output["safe_action"]
    card_dict["donots"] = llm_output["donots"]

    return {
        "success": True,
        "response_type": "RAG",
        "context_analysis": llm_output["context_analysis"],
        "safe_action": llm_output["safe_action"],
        "donots": llm_output["donots"],
        "matched_card": EvidenceCardResponse(**card_dict),
        "matched_chunk": {
            "chunk_id": best_match["chunk_id"],
            "document_id": best_match["document_id"],
            "source_kind": best_match["source_kind"],
            "source_ref": best_match["source_ref"],
            "title": best_match["title"],
            "source_url": best_match["source_url"],
            "similarity": round(best_match["similarity"], 4)
        },
        "sources": [
            {
                "chunk_id": m["chunk_id"],
                "document_id": m["document_id"],
                "source_kind": m["source_kind"],
                "source_ref": m["source_ref"],
                "title": m["title"],
                "source_url": m["source_url"],
                "similarity": round(m["similarity"], 4)
            }
            for m in matches
        ],
        "confidence": card_dict["reliability_score"],
        "confidence_level": card_dict["confidence_level"]
    }
