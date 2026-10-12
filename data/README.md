# THƯ MỤC LƯU TRỮ DỮ LIỆU (DATA ARCHITECTURE - AISC'26)

Hệ thống quản lý dữ liệu theo kiến trúc đa tầng (Multi-tier Data Lake to Knowledge Mart):

```
data/
├── 01_data_lake_raw/           <-- Nơi chứa các tài liệu thô thu thập thực tế (PDF, Word, Excel, CSV)
│   ├── japan/                  <-- Cẩm nang JASSO, ISA, tài liệu Shiyakusho...
│   ├── korea/                  <-- Hướng dẫn MOFA, NHIS, quy định du học...
│   └── australia/              <-- Luật Fair Work Ombudsman, Visa 500, ATO...
├── 02_transformed/             <-- Dữ liệu sau khi xử lý cắt đoạn (Chunking) & khử PII
└── 03_rag_knowledge_mart/      <-- JSON/CSV chuẩn hóa cấu trúc Thẻ Bằng Chứng (Evidence Cards)
```

### Quy trình nạp dữ liệu khi có tài liệu thô:
1. Thả file tài liệu gốc vào `data/01_data_lake_raw/<quoc_gia>/`
2. Chạy pipeline nạp tự động:
   ```bash
   python scripts/pipeline_ingest.py
   ```
3. Hệ thống sẽ tự động:
   - Đọc văn bản thô
   - Cắt đoạn có overlap (Window: 1000 ký tự, Overlap: 200 ký tự - theo giáo trình AI Viet Nam)
   - Khử định danh thông tin cá nhân PII (số điện thoại, email)
   - Trích xuất cấu trúc 4 phần của Thẻ Bằng Chứng (Bối cảnh, Thực tế kiểm chứng, Hành vi an toàn, Điều cấm kỵ)
   - Sinh vector nhúng (Embedding) và upsert vào cơ sở dữ liệu `evidence_cards` & `evidence_vectors` trong PostgreSQL pgvector.
