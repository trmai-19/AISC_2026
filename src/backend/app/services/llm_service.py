import logging
import json
from typing import Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Trợ lý Phiên Dịch Văn Hóa Số (DCI Copilot) thuộc đề án AISC'26 - Team Asteria (UIT - ĐHQG TP.HCM).
Nhiệm vụ của bạn là hỗ trợ người Việt Nam thích nghi văn hóa tại Nhật Bản, Hàn Quốc hoặc Australia.

NGUYÊN TẮC BẮT BUỘC (GROUNDING & AN TOÀN):
1. Dựa HOÀN TOÀN vào đoạn Bằng chứng (Evidence Card) được cung cấp dưới đây để trả lời.
2. Tuyệt đối KHÔNG tự suy diễn, KHÔNG đưa ra thông tin ngoài phạm vi đã kiểm chứng.
3. Đặt temperature = 0, phong cách giao tiếp điềm tĩnh, chuẩn mực, thấu hiểu.
4. Trả về đúng định dạng JSON có 3 trường sau (KHÔNG dùng markdown code block, chỉ JSON thuần):
{
  "context_analysis": "Phân tích bối cảnh và nguyên nhân văn hóa của tình huống...",
  "safe_action": "Các bước hành động an toàn, cụ thể và lịch sự nên thực hiện...",
  "donots": "Những điều tối kỵ, hành vi cấm kỵ hoặc rủi ro pháp lý tuyệt đối cần tránh..."
}
"""

async def generate_structured_response(
    query: str,
    evidence_card: Dict[str, Any],
    country: str
) -> Dict[str, str]:
    """
    Sinh câu trả lời cấu trúc 4 phần thông qua LLM (Gemini API) hoặc Fallback Synthesis.
    """
    context_text = f"""
TIÊU ĐỀ THẺ: {evidence_card.get('title')}
BỐI CẢNH ÁP DỤNG: {evidence_card.get('context')}
NỘI DUNG ĐÃ KIỂM CHỨNG: {evidence_card.get('verified_content')}
HÀNH VI AN TOÀN ĐỀ XUẤT: {evidence_card.get('safe_action')}
ĐIỀU CẦN TRÁNH: {evidence_card.get('donots')}
TỔ CHỨC XÁC MINH: {evidence_card.get('organization_name', 'Cơ quan thẩm quyền')}
"""
    # Nếu có GEMINI_API_KEY, gọi Google Gemini API
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT}\n\n[NGỮ CẢNH BẰNG CHỨNG]:\n{context_text}\n\n[CÂU HỎI]: {query}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json"
                }
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidate = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(candidate)
                    return {
                        "context_analysis": parsed.get("context_analysis", evidence_card.get('context')),
                        "safe_action": parsed.get("safe_action", evidence_card.get('safe_action')),
                        "donots": parsed.get("donots", evidence_card.get('donots'))
                    }
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Gemini API, chuyển sang chế độ Grounded Template Fallback: {e}")

    # Chế độ Grounded Fallback: Sử dụng thông tin chính xác 100% từ Evidence Card
    country_name = "Nhật Bản" if country == "JP" else ("Hàn Quốc" if country == "KR" else "Australia")
    return {
        "context_analysis": f"Trong môi trường đời sống và làm việc tại {country_name}, tình huống này thuộc phạm vi quy chuẩn ứng xử: '{evidence_card.get('title')}'. Theo thông tin kiểm chứng: {evidence_card.get('verified_content')}",
        "safe_action": evidence_card.get("safe_action", ""),
        "donots": evidence_card.get("donots", "")
    }
