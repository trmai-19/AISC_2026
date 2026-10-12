-- =====================================================================
-- AISC 2026 - POSTGRESQL DATABASE SCHEMA (PostgreSQL 16 + pgvector)
-- Dự án: Phiên Dịch Văn Hoá Số (Digital Cultural Interpreter - DCI)
-- Đội thi: Asteria - Trường ĐH Công nghệ Thông tin (UIT - ĐHQG TP.HCM)
-- Kiến trúc: Enterprise Scalable Knowledge Mart (10 Bảng)
-- =====================================================================

-- 0. KÍCH HOẠT EXTENSION PGVECTOR PHỤC VỤ RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- Xóa bảng cũ (theo thứ tự phụ thuộc) để đảm bảo tính idempotent
DROP TABLE IF EXISTS evidence_vectors CASCADE;
DROP TABLE IF EXISTS evidence_cards CASCADE;
DROP TABLE IF EXISTS knowledge_sources CASCADE;
DROP TABLE IF EXISTS admin_queue_logs CASCADE;
DROP TABLE IF EXISTS contribution_challenges CASCADE;
DROP TABLE IF EXISTS community_contributions CASCADE;
DROP TABLE IF EXISTS user_feedbacks CASCADE;
DROP TABLE IF EXISTS chat_history CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- =====================================================================
-- PHẦN 1: TẦNG APPLICATION / OLTP (7 BẢNG VẬN HÀNH & TƯƠNG TÁC)
-- =====================================================================

-- Bảng 1: users - Định danh & phân quyền
CREATE TABLE users (
    user_id        VARCHAR(36)   NOT NULL,
    email          VARCHAR(100)  NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    full_name      VARCHAR(100)  NOT NULL,
    role           VARCHAR(20)   NOT NULL,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_users PRIMARY KEY (user_id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_role CHECK (role IN ('GUEST', 'USER', 'ADMIN'))
);

-- Bảng 2: user_profiles - Ngữ cảnh cá nhân hóa (1-1 với users)
CREATE TABLE user_profiles (
    profile_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         VARCHAR(36)  NOT NULL UNIQUE,
    target_country  VARCHAR(10)  NULL,   -- JP, KR, AU
    purpose         VARCHAR(50)  NULL,   -- DU_HOC, LAO_DONG, DINH_CU
    stage           VARCHAR(50)  NULL,   -- PREPARING, RECENT_ARRIVED, LIVING_STUDYING, RETURNED
    CONSTRAINT fk_user_profiles_users FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_profiles_purpose CHECK (purpose IS NULL OR purpose IN ('DU_HOC', 'LAO_DONG', 'DINH_CU'))
);

-- Bảng 3: chat_history - Lịch sử hội thoại RAG Copilot
CREATE TABLE chat_history (
    message_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          VARCHAR(36)   NULL,
    sender_type      VARCHAR(10)   NOT NULL,
    content          TEXT          NOT NULL,
    matched_card_id  VARCHAR(50)   NULL,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_history_users FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE SET NULL,
    CONSTRAINT ck_chat_history_sender_type CHECK (sender_type IN ('USER', 'BOT'))
);

-- Bảng 4: user_feedbacks - Đánh giá / báo lỗi thẻ bằng chứng (LIKE/REPORT)
CREATE TABLE user_feedbacks (
    feedback_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id           VARCHAR(36)  NOT NULL,
    evidence_card_id  VARCHAR(50)  NOT NULL,
    feedback_type     VARCHAR(20)  NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_feedbacks_users FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_feedbacks_type CHECK (feedback_type IN ('LIKE', 'REPORT'))
);

-- Bảng 5: community_contributions - Đóng góp khảo sát & trải nghiệm cộng đồng
CREATE TABLE community_contributions (
    contribution_id  VARCHAR(50)   NOT NULL PRIMARY KEY,  -- vd: REV-2026-001
    user_id          VARCHAR(36)   NOT NULL,
    country_code     VARCHAR(10)   NOT NULL,              -- JP, KR, AU
    domain_id        VARCHAR(50)   NOT NULL,              -- giao_tiep, phap_ly, nha_o, tai_chinh...
    exp_title        VARCHAR(255)  NOT NULL,
    exp_text         TEXT          NOT NULL,
    prep_level       INT           NULL,                  -- Thang 1 - 5
    use_intention    INT           NULL,                  -- Thang 1 - 5
    status           VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    submitted_at     TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cc_users FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT ck_cc_prep_level CHECK (prep_level IS NULL OR (prep_level BETWEEN 1 AND 5)),
    CONSTRAINT ck_cc_use_intention CHECK (use_intention IS NULL OR (use_intention BETWEEN 1 AND 5)),
    CONSTRAINT ck_cc_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
);

-- Bảng 6: contribution_challenges - Khó khăn gặp phải (Quan hệ 1-N)
CREATE TABLE contribution_challenges (
    id               INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contribution_id  VARCHAR(50) NOT NULL,
    challenge_code   VARCHAR(50) NOT NULL,
    CONSTRAINT fk_cch_contributions FOREIGN KEY (contribution_id)
        REFERENCES community_contributions (contribution_id) ON DELETE CASCADE,
    CONSTRAINT uq_cch_contribution_code UNIQUE (contribution_id, challenge_code)
);

-- Bảng 7: admin_queue_logs - Audit log kiểm duyệt của Ban Quản Trị
CREATE TABLE admin_queue_logs (
    log_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    admin_user_id  VARCHAR(36) NOT NULL,
    reference_id   VARCHAR(50) NOT NULL,
    action_taken   VARCHAR(20) NOT NULL,
    processed_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aql_users FOREIGN KEY (admin_user_id)
        REFERENCES users (user_id),
    CONSTRAINT ck_aql_action CHECK (action_taken IN ('APPROVE', 'REJECT'))
);

-- =====================================================================
-- PHẦN 2: TẦNG KNOWLEDGE MART & RAG VECTOR STORE (3 BẢNG TRI THỨC)
-- =====================================================================

-- Bảng 8: knowledge_sources - Danh mục tài liệu gốc & cơ quan kiểm chuẩn
CREATE TABLE knowledge_sources (
    source_id          VARCHAR(50)   PRIMARY KEY,  -- vd: SRC-JP-JASSO-01
    country_code       VARCHAR(10)   NOT NULL,     -- JP, KR, AU, GLOBAL
    organization_name  VARCHAR(150)  NOT NULL,     -- JASSO, Fair Work, MOFA, ISA...
    source_type        VARCHAR(100)  NOT NULL,     -- Cơ quan chính phủ, Tài liệu văn hóa chuẩn...
    document_title     VARCHAR(255)  NOT NULL,     -- Tên cẩm nang / tài liệu gốc
    document_url       TEXT          NULL,
    published_date     DATE          NULL,
    valid_until        DATE          NULL,         -- Theo dõi độ tươi (Freshness)
    reliability_score  INT           DEFAULT 98,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Bảng 9: evidence_cards - Thẻ tri thức văn hóa & quy chuẩn ứng xử (Payload)
CREATE TABLE evidence_cards (
    card_id            VARCHAR(50)   PRIMARY KEY,  -- vd: EVD-JP-001
    source_id          VARCHAR(50)   NULL,
    country_code       VARCHAR(10)   NOT NULL,     -- JP, KR, AU
    domain_id          VARCHAR(50)   NOT NULL,     -- 9 lĩnh vực chuẩn hoá
    title              VARCHAR(255)  NOT NULL,
    context            TEXT          NOT NULL,     -- Bối cảnh tình huống
    verified_content   TEXT          NOT NULL,     -- Nội dung đã kiểm chứng
    safe_action        TEXT          NOT NULL,     -- Hành vi an toàn đề xuất
    donots             TEXT          NOT NULL,     -- Điều tuyệt đối cần tránh
    reliability_score  INT           DEFAULT 95,
    confidence_level   VARCHAR(50)   DEFAULT 'Rất cao (98%)',
    status             VARCHAR(20)   NOT NULL DEFAULT 'APPROVED',
    verified_date      DATE          DEFAULT CURRENT_DATE,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ec_source FOREIGN KEY (source_id)
        REFERENCES knowledge_sources (source_id) ON DELETE SET NULL,
    CONSTRAINT ck_ec_status CHECK (status IN ('PENDING', 'APPROVED', 'OUTDATED', 'REJECTED'))
);

-- Bảng 10: evidence_vectors - Kho vector nhúng tách rời (Tối ưu I/O & RAM Cache)
CREATE TABLE evidence_vectors (
    vector_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_id          VARCHAR(50) NOT NULL UNIQUE,
    embedding_model  VARCHAR(50) NOT NULL DEFAULT 'bge-m3',
    embedding        VECTOR(768) NOT NULL,         -- Vector nhúng 768 chiều
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ev_card FOREIGN KEY (card_id)
        REFERENCES evidence_cards (card_id) ON DELETE CASCADE
);

-- =====================================================================
-- PHẦN 3: TỐI ƯU HÓA CHỈ MỤC (INDEXING & PERFORMANCE)
-- =====================================================================

-- Chỉ mục tìm kiếm Vector Cosine bằng giải thuật HNSW (Hierarchical Navigable Small World)
CREATE INDEX idx_evidence_vectors_hnsw 
    ON evidence_vectors 
    USING hnsw (embedding vector_cosine_ops);

-- Chỉ mục lọc đa thuộc tính trên Application & Knowledge Mart
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_chat_history_user_created ON chat_history (user_id, created_at);
CREATE INDEX idx_user_feedbacks_card ON user_feedbacks (evidence_card_id);
CREATE INDEX idx_cc_status_submitted ON community_contributions (status, submitted_at);
CREATE INDEX idx_cc_country_domain ON community_contributions (country_code, domain_id);
CREATE INDEX idx_aql_reference ON admin_queue_logs (reference_id);
CREATE INDEX idx_evidence_cards_filter ON evidence_cards (country_code, domain_id, status);
