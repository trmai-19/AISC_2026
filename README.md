# PHIÊN DỊCH VĂN HOÁ SỐ (DIGITAL CULTURAL INTERPRETER - DCI)

> **Cuộc thi**: Advanced Information Systems Contest 2026 (AISC'26)  
> **Đơn vị**: Trường Đại học Công nghệ Thông tin – ĐHQG TP.HCM (UIT)  
> **Đội thi**: Asteria  

---

## 📖 Giới thiệu Đề án

**Phiên Dịch Văn Hoá Số (DCI)** là nền tảng trợ lý thông minh hỗ trợ du học sinh, người lao động và cộng đồng người Việt hòa nhập văn hóa tại nước ngoài (Nhật Bản, Hàn Quốc, Australia).

Hệ thống kết hợp giữa:
1. **Cơ chế RAG (Retrieval-Augmented Generation) kiểm chứng 2 giai đoạn** trên nền tảng **PostgreSQL 16 + pgvector**, ngăn chặn hoàn toàn ảo giác (Hallucination) với ngưỡng từ chối trả lời tin cậy (Confidence Threshold: 0.75).
2. **Kho Bằng Chứng (Evidence Hub)** gồm các Thẻ Bằng Chứng (Evidence Cards) được chuẩn hóa theo 9 lĩnh vực đời sống, trích dẫn minh bạch từ các cơ quan chính phủ sở tại (JASSO, ISA, MOFA, Fair Work Ombudsman).
3. **Quy trình thẩm định đóng góp cộng đồng (Community Ingestion & Admin Audit)** với cơ chế khử định danh thông tin cá nhân (PII Sanitization) tự động.

---

## 🛠️ Yêu cầu môi trường (Prerequisites)

Trước khi chạy, đảm bảo máy tính của bạn đã cài đặt:
- **Docker Desktop** (Đang mở và hoạt động)
- **Python 3.10 – 3.12** (Khuyến nghị 3.11 hoặc 3.12)
- **Git**

---

## 🚀 Hướng dẫn khởi chạy (Execution Guide)

Hệ thống hỗ trợ 2 phương án khởi chạy linh hoạt tùy theo nhu cầu:

---

### ⭐ PHƯƠNG ÁN 1: KHỞI CHẠY TRỌN GÓI BẰNG DOCKER (KHUYẾN NGHỊ CAO NHẤT)

> Áp dụng cho mọi thành viên: **Không cần cài đặt Python, không cần cấu hình venv**, máy Mac/Windows/Linux đều chạy giống nhau 100%.

1. **Chỉ cần chạy 1 lệnh duy nhất** (hoặc nhấp đúp file `docker_start.bat` trên Windows):
   ```powershell
   docker compose up -d --build
   ```
2. **Hệ thống tự động khởi chạy 3 dịch vụ**:
   * 🐘 **Database (PostgreSQL 16 + pgvector)**: Cổng `5432` (Tự động nạp schema 10 bảng và 300 mẫu khảo sát).
   * 🚀 **Backend (FastAPI + RAG Engine)**: Cổng `8000` -> Xem Swagger Docs tại: **[http://localhost:8000/docs](http://localhost:8000/docs)**.
   * 🌐 **Frontend (Nginx Web UI)**: Cổng `3000` -> Mở giao diện tại: **[http://localhost:3000](http://localhost:3000)**.

> 🔥 **Cơ chế Hot-Reload**: Thư mục `src/backend` và `src/ui` được ánh xạ trực tiếp (volume mount). Bất kỳ khi nào bạn sửa code Python hoặc sửa giao diện HTML/CSS/JS trong VS Code, hệ thống **tự động cập nhật ngay lập tức trong 0.5s** mà không cần build lại Docker!

Để dừng hệ thống khi không dùng nữa:
```powershell
docker compose down
```
*(Hoặc nhấp đúp file `docker_stop.bat`)*

---

### 💻 PHƯƠNG ÁN 2: CHẠY NATIVE TRÊN MÁY (LOCAL DEVELOPMENT)

Dành cho thành viên muốn chạy trực tiếp mã nguồn Python bên ngoài Docker để debug:

1. **Khởi động riêng Database**:
   ```powershell
   docker compose up -d postgres
   ```
2. **Khởi động Backend**:
   * **Cách 1-Click nhanh nhất**: Nhấp đúp chuột vào file **`run_backend.bat`** (tự tạo `venv`, tự cài thư viện và bật server).
   * **Cách thủ công**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     pip install -r src/backend/requirements.txt
     python src/backend/run.py
     ```
3. **Mở Giao diện Frontend**:
   Mở trực tiếp file `src/ui/index.html` trên trình duyệt.

---

### Bước 4: Kiểm tra API tương tác (Swagger UI)

Mở trình duyệt web và truy cập:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

Tại đây bạn có thể thử nghiệm trực tiếp các API:
- `GET /health`: Kiểm tra kết nối cơ sở dữ liệu.
- `POST /api/v1/chat/message`: Thử hỏi tình huống văn hóa (vd: *"Vô tình làm vỡ đĩa tại quán baito"*).
- `GET /api/v1/evidence`: Tra cứu danh sách Thẻ Bằng Chứng có lọc quốc gia và lĩnh vực.
- `POST /api/v1/survey/submit`: Gửi phiếu khảo sát thực tế (tự động ẩn PII).

---

### Bước 5: Khởi chạy Giao diện Web (Frontend)

Mở trực tiếp file:
📁 **`src/ui/index.html`** bằng trình duyệt bất kỳ (nhấp đúp chuột hoặc dùng tiện ích Live Server trong VSCode).

* **Góc trên bên phải Header**: Sẽ hiển thị đèn xanh **`🟢 API: Online (pgvector)`**.
* **Trợ lý AI Copilot**: Khi gửi câu hỏi, hệ thống sẽ gọi trực tiếp PostgreSQL pgvector và trả về phản hồi 4 phần chuẩn mực kèm trích dẫn nguồn.
* **Chế độ ngoại tuyến (Offline fallback)**: Nếu Backend chưa bật, Web UI sẽ tự động chuyển sang chế độ Standby/Mock mà không gây gián đoạn trải nghiệm người dùng.

---

## 📂 Quy trình nạp thêm tài liệu thô (Data Ingestion Pipeline)

Khi thu thập được thêm các tài liệu chính thống mới (PDF, TXT, Markdown):

1. Đặt các tệp tài liệu gốc vào đúng thư mục quốc gia tương ứng:
   - Nhật Bản: `data/01_data_lake_raw/japan/`
   - Hàn Quốc: `data/01_data_lake_raw/korea/`
   - Australia: `data/01_data_lake_raw/australia/`
2. Chạy pipeline ETL tự động:
   ```powershell
   python scripts/pipeline_ingest.py
   ```
   Hệ thống sẽ tự động:
   - Trích xuất văn bản từ tệp PDF/TXT.
   - Cắt đoạn (Text Chunking) với Window: 1000 ký tự, Overlap: 200 ký tự (theo giáo trình AI Viet Nam).
   - Khử định danh PII (SĐT, Email).
   - Sinh vector nhúng và upsert trực tiếp vào bảng `evidence_cards` & `evidence_vectors` trong PostgreSQL.

---

## 📁 Cấu trúc thư mục dự án

```
AISC_2026/
├── database/                   # Tầng cơ sở dữ liệu PostgreSQL
│   ├── 01_schema.sql           # Schema 10 bảng + pgvector HNSW index
│   └── 02_mock_data.sql        # Dữ liệu hạt giống chuẩn hóa khớp KPI đề án
├── data/                       # Kiến trúc Data Lake đa tầng
│   ├── 01_data_lake_raw/       # Nơi lưu tài liệu thô thu thập theo quốc gia
│   └── README.md               # Hướng dẫn quản trị dữ liệu
├── docker-compose.yml          # Cấu hình container pgvector/pgvector:pg16
├── scripts/                    # Scripts tự động hóa
│   └── pipeline_ingest.py      # Pipeline ETL nạp dữ liệu thô vào pgvector
├── src/
│   ├── backend/                # Mã nguồn FastAPI Backend
│   │   ├── app/
│   │   │   ├── models/         # SQLAlchemy ORM Models (10 bảng)
│   │   │   ├── schemas/        # Pydantic Schemas xác thực dữ liệu
│   │   │   ├── routers/        # API Endpoints (chat, evidence, survey, admin, auth)
│   │   │   ├── services/       # RAG Vector Search & LLM Engine
│   │   │   ├── config.py       # Cấu hình hệ thống
│   │   │   ├── database.py     # Kết nối Database Engine & Session
│   │   │   └── main.py         # Điểm khởi chạy ứng dụng FastAPI & CORS
│   │   ├── requirements.txt    # Danh mục thư viện Python phụ thuộc
│   │   └── run.py              # Script khởi động máy chủ Uvicorn
│   └── ui/                     # Giao diện người dùng Web Frontend
│       ├── index.html          # Giao diện chính (Dual-mode)
│       ├── styles.css          # Hệ thống CSS thiết kế hiện đại
│       ├── app.js              # Xử lý tương tác & kết nối REST API kép
│       └── data.js             # Dữ liệu tĩnh dự phòng (Mock data)
├── .gitignore                  # Bỏ qua venv, .env, ảnh và tài liệu nặng
└── README.md                   # Hướng dẫn vận hành dự án
```

---

## 👥 Thành viên nhóm Asteria (UIT)

| STT | Họ và Tên | MSSV | Vai trò |
|---|---|---|---|
| 1 | Trần Đình Phúc | 24521397 | Trưởng nhóm |
| 2 | Huỳnh Đăng Khoa | 24522074 | Thành viên |
| 3 | Nguyễn Hoài Nam | 24521109 | Thành viên |
| 4 | Nguyễn Triệu Hoàng | 23520534 | Thành viên |
| 5 | Đặng Trúc Mai | 24521037 | Thành viên |
