import logging
import json
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Trợ lý Phiên Dịch Văn Hóa Số (DCI Copilot) thuộc đề án AISC'26 - Team Asteria (UIT - ĐHQG TP.HCM).
Nhiệm vụ của bạn là hỗ trợ người Việt Nam thích nghi văn hóa tại Nhật Bản (JP), Hàn Quốc (KR) hoặc Australia (AU).

NGUYÊN TẮC BẮT BUỘC (GROUNDING & AN TOÀN):
1. Dựa HOÀN TOÀN vào các đoạn Bằng chứng RAG được cung cấp (được đánh dấu [S1], [S2]...) để trả lời.
2. Phân biệt rõ nguồn gốc thông tin:
   - Nguồn chính thống (EXTERNAL: JNTO, Cultural Atlas): Nêu quy chuẩn văn hóa, phép lịch sự chính thức.
   - Trải nghiệm cộng đồng (COMMUNITY): Nêu bài học và kinh nghiệm thực tế của người Việt sinh sống tại nước sở tại.
3. Tuyệt đối KHÔNG tự suy diễn, KHÔNG đưa ra thông tin hoặc URL nằm ngoài bằng chứng.
4. Nếu bằng chứng không đủ để trả lời trọn vẹn, hãy nói rõ phạm vi dữ liệu hiện có.
5. Đặt temperature = 0, phong cách giao tiếp điềm tĩnh, chuẩn mực, thấu hiểu.
6. Trả về đúng định dạng JSON có 3 trường sau (KHÔNG dùng markdown code block, chỉ JSON thuần):
{
  "context_analysis": "Phân tích bối cảnh và nguyên nhân văn hóa của tình huống (kèm trích dẫn nguồn [S1], [S2] nếu có)...",
  "safe_action": "Các bước hành động an toàn, cụ thể và lịch sự nên thực hiện...",
  "donots": "Những điều tối kỵ, hành vi cấm kỵ hoặc rủi ro tuyệt đối cần tránh..."
}
"""

async def generate_structured_response(
    query: str,
    evidence_card: Dict[str, Any],
    country: str,
    matches: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Sinh câu trả lời cấu trúc 4 phần thông qua LLM (Gemini API) hoặc Fallback Grounding.
    Hỗ trợ danh sách các matches từ kho RAG E5 mới.
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

    # Nếu có GEMINI_API_KEY, gọi Google Gemini API
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT}\n\n[QUỐC GIA]: {country_name} ({country})\n\n[NGỮ CẢNH BẰNG CHỨNG RAG]:\n{context_text}\n\n[CÂU HỎI NGƯỜI DÙNG]: {query}"}
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
                        "context_analysis": parsed.get("context_analysis", evidence_card.get('context', '')),
                        "safe_action": parsed.get("safe_action", evidence_card.get('safe_action', '')),
                        "donots": parsed.get("donots", evidence_card.get('donots', ''))
                    }
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Gemini API, chuyển sang chế độ Grounded Template Fallback: {e}")

    # Chế độ Grounded Fallback: Sử dụng thông tin chính xác từ tài liệu đã đối soát
    title = evidence_card.get('title', 'Quy chuẩn ứng xử')
    verified_content = evidence_card.get('verified_content', '')
    safe_action = evidence_card.get("safe_action", "")
    donots = evidence_card.get("donots", "")

    if not safe_action and verified_content:
        # Nếu là chunk trích xuất chưa có action tách riêng, tạo hành động an toàn khuyến nghị từ nội dung
        safe_action = f"Tuân thủ đúng phép lịch sự và quy tắc ứng xử theo trích dẫn: {verified_content[:200]}..."
    if not donots and verified_content:
        donots = "Tránh các hành vi bất lịch sự, thất lễ hoặc vi phạm quy định địa phương khi giao tiếp."

    return {
        "context_analysis": f"Tại {country_name}, tình huống này liên quan đến quy chuẩn: '{title}'. Theo tài liệu đối soát: {verified_content[:350]}...",
        "safe_action": safe_action,
        "donots": donots
    }
