import logging
import hashlib
import math
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.repositories.evidence_repository import EvidenceRepository
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

# =====================================================================
# HÀM CHUNKING VỚI OVERLAP (KẾ THỪA TỪ TÀI LIỆU AI VIET NAM AIO 2026)
# =====================================================================
def chunk_text(text_content: str, size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Cắt nhỏ văn bản thành các đoạn (chunks) có độ dài tối đa 'size' ký tự,
    với 'overlap' ký tự trùng lặp giữa 2 đoạn liên tiếp để bảo toàn ngữ cảnh.
    """
    if not text_content:
        return []
    paras = [p.strip() for p in text_content.split("\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        while len(p) > size:
            if cur:
                chunks.append(cur.strip())
            cur = ""
            chunks.append(p[:size].strip())
            p = p[size - overlap:]
        if len(cur) + len(p) + 1 <= size:
            cur += p + "\n"
        else:
            if cur:
                chunks.append(cur.strip())
            cur = (cur[-overlap:] + p + "\n") if overlap else (p + "\n")
    if cur.strip():
        chunks.append(cur.strip())
    return chunks

# =====================================================================
# SINH VECTOR TƯƠNG ĐỒNG BẰNG HASHING VECTORIZER (768 DIMENSIONS)
# =====================================================================
def generate_query_vector(text_content: str, country: str = "") -> List[float]:
    """
    Tạo vector 768 chiều chuẩn hóa L2 (L2-Normalized Dense Vector) dựa trên 
    Feature Hashing của từ và character n-grams.
    - Đảm bảo tính nhất quán toán học 100% không phụ thuộc network/API ngoài.
    - Chống lỗi gõ phím/chính tả nhờ character trigram buckets.
    - Tương thích hoàn toàn với chỉ mục HNSW trên pgvector.
    """
    dim = 768
    vec = [0.0] * dim
    clean_text = text_content.lower().strip()
    if not clean_text:
        return vec

    tokens = re.findall(r'\w+', clean_text)
    char_trigrams = [clean_text[i:i+3] for i in range(max(0, len(clean_text) - 2))]
    all_features = tokens + char_trigrams

    for feat in all_features:
        h = int(hashlib.md5(feat.encode('utf-8')).hexdigest(), 16)
        bucket = h % dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        vec[bucket] += sign

    norm = math.sqrt(sum(x * x for x in vec))
    return [float(x / norm) for x in vec] if norm > 0 else vec

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
                "Tôi có thể giúp bạn giải đáp các tình huống ứng xử, giao tiếp, nhà ở, việc làm hoặc thủ tục thực tế. "
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
                "Tôi có thể giúp bạn giải đáp các quy chuẩn văn hóa, cách xử lý tình huống phát sinh và các quy định pháp lý – hành chính đã được đối soát chính thống."
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
    Thực thi quy trình RAG động không hardcode:
    1. Kiểm tra Guardrail hội thoại cơ bản (chào hỏi, cảm ơn, danh tính)
    2. Dynamic Hybrid Search qua EvidenceRepository (Vector + Trigram + Full-text)
    3. Ngưỡng tin cậy toán học (CONFIDENCE_THRESHOLD):
       Tự động từ chối nếu không thuộc phạm vi thông tin quy chuẩn của hệ thống.
    4. Gọi LLM định dạng câu trả lời cấu trúc 4 phần dựa trên Evidence Card.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "success": False,
            "response_type": "OUT_OF_SCOPE",
            "refusal_message": "Vui lòng nhập câu hỏi để hệ thống hỗ trợ bạn."
        }

    # 1. Kiểm tra ý định hội thoại cơ bản (Chào hỏi / Cảm ơn / Danh tính)
    smalltalk_response = detect_conversational_intent(clean_query, country)
    if smalltalk_response:
        return smalltalk_response

    # 2. Sinh vector biểu diễn câu hỏi
    query_vec = generate_query_vector(clean_query, country)

    # 3. Truy vấn Hybrid Search qua Repository
    search_results = EvidenceRepository.search_hybrid(
        db=db,
        query=clean_query,
        country=country,
        query_vector=query_vec,
        limit=1
    )

    # 4. Kiểm soát ngưỡng an toàn toán học (Chống suy diễn ảo giác)
    matched_card = None
    similarity_score = 0.0

    if search_results:
        matched_card, similarity_score = search_results[0]

    # Nếu không có thẻ hoặc điểm tương đồng thấp hơn ngưỡng cho phép -> Báo ngoài phạm vi cung cấp
    if not matched_card or similarity_score < settings.CONFIDENCE_THRESHOLD:
        country_name = COUNTRY_MAP.get(country, "nước sở tại")
        logger.info(
            f"RAG Refusal triggered: query='{clean_query}', country='{country}', "
            f"best_score={similarity_score:.4f}, threshold={settings.CONFIDENCE_THRESHOLD}"
        )
        return {
            "success": False,
            "response_type": "OUT_OF_SCOPE",
            "refusal_message": (
                f"Câu trả lời cho vấn đề này hiện không thuộc phạm vi thông tin và quy chuẩn văn hóa mà hệ thống DCI cung cấp tại {country_name}. "
                "Bạn có thể đặt câu hỏi về các chủ đề văn hóa ứng xử, giao tiếp, nhà ở, lao động hoặc thủ tục đời sống (Ví dụ: quy chuẩn làm thêm baito, phân loại rác, văn hóa tiền tip, v.v.) để tôi hỗ trợ bạn tốt nhất nhé!"
            )
        }

    # 4. Chuẩn bị thông tin nguồn đối soát chính thống
    org_name = matched_card.source.organization_name if matched_card.source else "Cơ quan thẩm quyền sở tại"
    doc_url = matched_card.source.document_url if matched_card.source else "#"

    card_dict = {
        "card_id": matched_card.card_id,
        "source_id": matched_card.source_id,
        "country_code": matched_card.country_code,
        "country_name": COUNTRY_MAP.get(matched_card.country_code, matched_card.country_code),
        "domain_id": matched_card.domain_id,
        "domain_name": DOMAIN_MAP.get(matched_card.domain_id, matched_card.domain_id),
        "title": matched_card.title,
        "context": matched_card.context,
        "verified_content": matched_card.verified_content,
        "safe_action": matched_card.safe_action,
        "donots": matched_card.donots,
        "reliability_score": matched_card.reliability_score,
        "confidence_level": matched_card.confidence_level,
        "status": matched_card.status or "APPROVED",
        "organization_name": org_name,
        "source_url": doc_url,
        "verified_date": matched_card.verified_date
    }

    # 5. Sinh câu trả lời có cấu trúc thông qua LLM (Grounded Output)
    llm_output = await generate_structured_response(clean_query, card_dict, country)

    return {
        "success": True,
        "response_type": "RAG",
        "context_analysis": llm_output["context_analysis"],
        "safe_action": llm_output["safe_action"],
        "donots": llm_output["donots"],
        "matched_card": card_dict,
        "confidence": matched_card.reliability_score,
        "confidence_level": matched_card.confidence_level
    }
