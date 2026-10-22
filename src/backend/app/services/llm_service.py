import logging
import json
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Trợ lý Phiên Dịch Văn Hóa Số (DCI Copilot) thuộc đề án AISC'26 - Team Asteria (UIT - ĐHQG TP.HCM).
Nhiệm vụ của bạn là hỗ trợ người Việt Nam thích nghi văn hóa tại Nhật Bản (JP), Hàn Quốc (KR) hoặc Australia (AU).

NGUYÊN TẮC BẮT BUỘC:
1. TRẢ LỜI ĐÚNG TRỌNG TÂM CÂU HỎI của người dùng một cách tự nhiên, thấu đáo, chuẩn mực và lịch sự.
2. ĐỐI SOÁT & TRÍCH DẪN: Kết hợp chặt chẽ các Bằng chứng RAG được cung cấp (được đánh dấu [S1], [S2]...) để đối soát. Nếu có nguồn liên quan, hãy trích dẫn mã nguồn [S1], [S2] trong phần phân tích bối cảnh.
3. PHÂN BIỆT RÕ BẢN CHẤT THÔNG TIN:
   - Nguồn chính thống (EXTERNAL: JNTO, Cultural Atlas, cơ quan chính phủ): Nêu rõ quy định, phép lịch sự và chuẩn mực chính thức.
   - Trải nghiệm cộng đồng (COMMUNITY): Nêu kinh nghiệm thực tế, bài học từ người Việt sinh sống tại nước sở tại.
4. NÊU RÕ BỐI CẢNH VĂN HÓA: Luôn giải thích nguyên nhân sâu xa vì sao người bản xứ có quy chuẩn hay phản ứng như vậy để người dùng thấu hiểu bản chất.
5. ĐỊNH DẠNG ĐẦU RA: Bắt buộc trả về đúng định dạng JSON có 3 trường sau (KHÔNG dùng markdown code block, chỉ JSON thuần):
{
  "context_analysis": "Câu trả lời trực tiếp cho câu hỏi của người dùng, phân tích bối cảnh và nguyên nhân văn hóa của tình huống (kèm trích dẫn nguồn [S1], [S2] nếu có)...",
  "safe_action": "Các bước hành động an toàn, cụ thể và lịch sự nên thực hiện...",
  "donots": "Những điều tối kỵ, hành vi cấm kỵ hoặc rủi ro tuyệt đối cần tránh..."
}
"""

CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-2.5-pro",
]

async def generate_structured_response(
    query: str,
    evidence_card: Dict[str, Any],
    country: str,
    matches: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Sinh câu trả lời cấu trúc 3 phần thông qua LLM (Google Gemini API) hoặc Fallback Grounding.
    Hỗ trợ danh sách các matches từ kho RAG E5 mới và tự động chuyển đổi mô hình dự phòng.
    """
    country_name = "Nhật Bản" if country == "JP" else ("Hàn Quốc" if country == "KR" else "Australia")

    # Xây dựng ngữ cảnh bằng chứng từ matches hoặc từ evidence_card
    if matches:
        context_blocks = []
        for idx, m in enumerate(matches, 1):
            source_type = "CHÍNH THỐNG (EXTERNAL)" if m.get("source_kind") == "EXTERNAL" else "CỘNG ĐỒNG (COMMUNITY)"
            url_str = m.get("source_url") or "Không có (Kinh nghiệm đóng góp từ cộng đồng)"
            context_blocks.append(
                f"[S{idx}] ({source_type}) Tiêu đề: {m.get('title')}\n"
                f"Nguồn: {m.get('source_ref')} | URL: {url_str}\n"
                f"Nội dung trích đoạn:\n{m.get('content')}"
            )
        context_text = "\n\n---\n\n".join(context_blocks)
    else:
        context_text = f"""
TIÊU ĐỀ THẺ: {evidence_card.get('title')}
BỐI CẢNH ÁP DỤNG: {evidence_card.get('context')}
NỘI DUNG ĐÃ KIỂM CHỨNG: {evidence_card.get('verified_content')}
HÀNH VI AN TOÀN ĐỀ XUẤT: {evidence_card.get('safe_action')}
ĐIỀU CẦN TRÁNH: {evidence_card.get('donots')}
TỔ CHỨC XÁC MINH: {evidence_card.get('organization_name', 'Cơ quan thẩm quyền')}
"""

    # Nếu có GEMINI_API_KEY, gọi Google Gemini API qua danh sách candidate models
    if settings.GEMINI_API_KEY:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"{SYSTEM_PROMPT}\n\n"
                                f"[QUỐC GIA]: {country_name} ({country})\n\n"
                                f"[NGỮ CẢNH BẰNG CHỨNG RAG]:\n{context_text}\n\n"
                                f"[CÂU HỎI CỦA NGƯỜI DÙNG]:\n{query}\n\n"
                                "Hãy trả lời trực tiếp, đầy đủ vào câu hỏi trên dựa trên bối cảnh và bằng chứng đã cho."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        for model_name in CANDIDATE_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidate = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        # Xóa bỏ markdown code block nếu có
                        if candidate.startswith("```"):
                            import re
                            candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
                            candidate = re.sub(r"\s*```$", "", candidate)
                        parsed = json.loads(candidate)
                        logger.info(f"LLM Gemini ({model_name}) sinh phản hồi thành công cho câu hỏi: '{query[:50]}'")
                        return {
                            "context_analysis": parsed.get("context_analysis", evidence_card.get('context', '')),
                            "safe_action": parsed.get("safe_action", evidence_card.get('safe_action', '')),
                            "donots": parsed.get("donots", evidence_card.get('donots', ''))
                        }
                    else:
                        logger.warning(f"Gemini API model {model_name} trả về mã {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Lỗi khi gọi Gemini model {model_name}: {e}")

    # Chế độ Grounded Fallback: Khi không có API key hoặc toàn bộ model Gemini đều lỗi mạng
    logger.warning("Toàn bộ gọi LLM thất bại, sử dụng Grounded Template Fallback.")
    title = evidence_card.get('title', 'Quy chuẩn ứng xử')
    verified_content = evidence_card.get('verified_content', '')
    safe_action = evidence_card.get("safe_action", "")
    donots = evidence_card.get("donots", "")

    if not safe_action and verified_content:
        safe_action = f"Tuân thủ đúng phép lịch sự và quy tắc ứng xử theo trích dẫn: {verified_content[:200]}..."
    if not donots and verified_content:
        donots = "Tránh các hành vi bất lịch sự, thất lễ hoặc vi phạm quy định địa phương khi giao tiếp."

    return {
        "context_analysis": f"Tại {country_name}, đối với câu hỏi '{query}', tài liệu văn hóa chính thống ('{title}') ghi nhận: {verified_content[:350]}...",
        "safe_action": safe_action,
        "donots": donots
    }

