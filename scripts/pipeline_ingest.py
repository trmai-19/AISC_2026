"""
DATA INGESTION PIPELINE (DATA LAKE -> TRANSFORMATION -> RAG KNOWLEDGE MART)
AISC 2026 - Team Asteria (UIT - ĐHQG TP.HCM)

Script này thực thi quy trình ETL tự động:
1. Quét tài liệu thô trong Data Lake (PDF, TXT, MD, CSV...)
2. Khử định danh PII (SĐT, Email)
3. Cắt đoạn văn bản (Text Chunking) với Window: 1000 ký tự, Overlap: 200 ký tự (AI Viet Nam)
4. Sinh vector nhúng (Embedding)
5. Nạp vào PostgreSQL (Evidence Cards & Evidence Vectors)
"""

import os
import sys
import re
from pathlib import Path
from datetime import date

# Thêm đường dẫn backend vào sys.path
backend_path = Path(__file__).resolve().parent.parent / "src" / "backend"
sys.path.append(str(backend_path))

try:
    from app.services.rag_service import chunk_text, generate_query_vector
    from app.database import SessionLocal
    from app.models.knowledge import KnowledgeSource, EvidenceCard, EvidenceVector
except ImportError as e:
    print(f"Lưu ý: {e}")
    print("Vui lòng đảm bảo đã cài đặt các thư viện trong src/backend/requirements.txt")

DATA_LAKE_DIR = Path(__file__).resolve().parent.parent / "data" / "01_data_lake_raw"

COUNTRY_MAP = {
    "japan": "JP",
    "korea": "KR",
    "australia": "AU"
}

def sanitize_pii(text: str) -> str:
    """Tự động phát hiện và ẩn thông tin nhận dạng cá nhân"""
    cleaned = re.sub(r'(\+?84|0)\d{9,10}', '[ĐÃ ẨN SĐT]', text)
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[ĐÃ ẨN EMAIL]', cleaned)
    return cleaned

def extract_text_from_file(file_path: Path) -> str:
    """Đọc nội dung văn bản từ các định dạng file phổ biến"""
    suffix = file_path.suffix.lower()
    if suffix in [".txt", ".md", ".csv"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text)
        except Exception as e:
            print(f"Lỗi khi đọc file PDF {file_path.name}: {e}")
            return ""
    return ""

def run_pipeline():
    print("=" * 65)
    print("🚀 AISC 2026 - BẮT ĐẦU CHẠY PIPELINE NẠP DỮ LIỆU DATA LAKE")
    print("=" * 65)

    if not DATA_LAKE_DIR.exists():
        DATA_LAKE_DIR.mkdir(parents=True, exist_ok=True)
        for country in ["japan", "korea", "australia"]:
            (DATA_LAKE_DIR / country).mkdir(exist_ok=True)
        print(f"✅ Đã khởi tạo cấu trúc thư mục Data Lake tại: {DATA_LAKE_DIR}")
        print("💡 Hãy thả các file tài liệu thô (.pdf, .txt, .md) vào các thư mục quốc gia tương ứng rồi chạy lại script.")
        return

    # Quét tất cả file trong Data Lake
    files = [f for f in DATA_LAKE_DIR.rglob("*.*") if f.is_file() and not f.name.startswith(".")]

    if not files:
        print(f"📂 Thư mục Data Lake hiện chưa có file thô nào.")
        print(f"Vui lòng thả tài liệu vào: {DATA_LAKE_DIR}")
        return

    print(f"🔍 Tìm thấy {len(files)} tài liệu thô cần xử lý:")
    for f in files:
        print(f"  - {f.relative_to(DATA_LAKE_DIR)}")

    # Xử lý từng file
    try:
        db = SessionLocal()
    except Exception as e:
        print(f"❌ Không thể kết nối cơ sở dữ liệu: {e}")
        print("💡 Hãy đảm bảo container PostgreSQL pgvector đang chạy: docker compose up -d")
        return

    total_chunks_processed = 0

    try:
        for f in files:
            # Xác định quốc gia từ thư mục cha
            parent_folder = f.parent.name.lower()
            country_code = COUNTRY_MAP.get(parent_folder, "GLOBAL")

            raw_text = extract_text_from_file(f)
            if not raw_text.strip():
                print(f"⚠️ Bỏ qua tệp rỗng hoặc không trích xuất được: {f.name}")
                continue

            cleaned_text = sanitize_pii(raw_text)
            chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=200)

            print(f"\n📄 Đang xử lý '{f.name}' ({country_code}) -> Cắt thành {len(chunks)} đoạn chunk...")

            for idx, chunk in enumerate(chunks):
                card_id = f"INGEST-{country_code}-{int(f.stat().st_mtime)%10000}-{idx+1:03d}"

                # Kiểm tra xem đã tồn tại chưa
                existing = db.query(EvidenceCard).filter(EvidenceCard.card_id == card_id).first()
                if existing:
                    continue

                card = EvidenceCard(
                    card_id=card_id,
                    source_id=f"SRC-{country_code}-RAW",
                    country_code=country_code,
                    domain_id="giao_tiep",
                    title=f"Tri thức trích xuất: {f.stem} (Đoạn {idx+1})",
                    context=f"Trích xuất tự động từ tài liệu {f.name} thuộc Data Lake.",
                    verified_content=chunk,
                    safe_action="Tuân thủ theo chỉ dẫn chính thức từ tài liệu trích xuất.",
                    donots="Tránh làm ngược lại các khuyến cáo trong tài liệu.",
                    reliability_score=90,
                    confidence_level="Đang thẩm định (90%)",
                    status="APPROVED",
                    verified_date=date.today()
                )
                db.add(card)
                db.flush()

                # Sinh vector nhúng
                vector_data = generate_query_vector(chunk)
                ev = EvidenceVector(
                    card_id=card_id,
                    embedding_model="bge-m3",
                    embedding=vector_data
                )
                db.add(ev)
                total_chunks_processed += 1

        db.commit()
        print(f"\n🎉 HOÀN THÀNH PIPELINE: Đã nạp thành công {total_chunks_processed} đoạn tri thức và vector vào PostgreSQL!")
    except Exception as err:
        db.rollback()
        print(f"❌ Xảy ra lỗi trong quá trình nạp: {err}")
    finally:
        db.close()

if __name__ == "__main__":
    run_pipeline()
