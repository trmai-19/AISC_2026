# =====================================================================
# DOCKERFILE CHO FASTAPI BACKEND - AISC 2026 (TEAM ASTERIA)
# Base Image: Python 3.11-slim (Tối ưu kích thước & ổn định cao)
# =====================================================================

FROM python:3.11-slim

# Ngăn Python tạo file .pyc và bật unbuffered log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết cho PostgreSQL client và compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các thư viện Python trước để tận dụng Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn backend vào container
COPY . .

EXPOSE 8000

# Khởi động Uvicorn với chế độ reload (Hot-reload khi sửa code)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
