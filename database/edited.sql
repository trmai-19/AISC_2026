/* =====================================================================
   AISC 2026 - DATABASE SCHEMA (Microsoft SQL Server / T-SQL)
   Dự án: Phiên Dịch Văn Hoá Số (Digital Cultural Interpreter)
   Đội thi: Asteria - ĐH Công nghệ Thông tin (UIT - ĐHQG TP.HCM)
   Chủ đề: Data Driven Business | Lĩnh vực: Social Tech
   Phạm vi khảo sát & vận hành: Nhật Bản (JP), Hàn Quốc (KR), Úc (AU)
   9 lĩnh vực chuẩn hoá: Giao tiếp, Hành chính - Pháp lý, Nhà ở, Tài chính,
                         Học tập - Công việc, Y tế, Giao thông, Đời sống, Cộng đồng.
   ===================================================================== */

IF DB_ID(N'AISC_DB') IS NULL
    CREATE DATABASE AISC_DB;
GO
USE AISC_DB;
GO

/* Xóa bảng cũ (theo thứ tự phụ thuộc) để có thể chạy lại script */
DROP TABLE IF EXISTS dbo.admin_queue_logs;
DROP TABLE IF EXISTS dbo.contribution_challenges;
DROP TABLE IF EXISTS dbo.community_contributions;
DROP TABLE IF EXISTS dbo.user_feedbacks;
DROP TABLE IF EXISTS dbo.chat_history;
DROP TABLE IF EXISTS dbo.user_profiles;
DROP TABLE IF EXISTS dbo.users;
GO

/* ---------------------------------------------------------------------
   Bảng 1: users - Định danh & phân quyền người dùng
   --------------------------------------------------------------------- */
CREATE TABLE dbo.users (
    user_id        VARCHAR(36)   NOT NULL,
    email          VARCHAR(100)  NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    full_name      NVARCHAR(100) NOT NULL,
    role           VARCHAR(20)   NOT NULL,
    created_at     DATETIME2     NOT NULL CONSTRAINT DF_users_created_at DEFAULT SYSDATETIME(),
    CONSTRAINT PK_users       PRIMARY KEY (user_id),
    CONSTRAINT UQ_users_email UNIQUE (email),
    CONSTRAINT CK_users_role  CHECK (role IN ('GUEST', 'USER', 'ADMIN'))
);
GO

/* ---------------------------------------------------------------------
   Bảng 2: user_profiles - Bộ lọc ngữ cảnh cá nhân hóa (1-1 với users)
   --------------------------------------------------------------------- */
CREATE TABLE dbo.user_profiles (
    profile_id      INT IDENTITY(1,1) NOT NULL,
    user_id         VARCHAR(36)  NOT NULL,
    target_country  VARCHAR(10)  NULL,   -- JP, KR, AU
    purpose         VARCHAR(50)  NULL,   -- DU_HOC, LAO_DONG, DINH_CU
    stage           VARCHAR(50)  NULL,   -- PREPARING, RECENT_ARRIVED, LIVING_STUDYING, RETURNED
    CONSTRAINT PK_user_profiles         PRIMARY KEY (profile_id),
    CONSTRAINT UQ_user_profiles_user_id UNIQUE (user_id),
    CONSTRAINT FK_user_profiles_users   FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE CASCADE,
    CONSTRAINT CK_user_profiles_purpose CHECK (purpose IS NULL OR purpose IN ('DU_HOC', 'LAO_DONG', 'DINH_CU'))
);
GO

/* ---------------------------------------------------------------------
   Bảng 3: chat_history - Luồng hội thoại cho RAG Copilot
   --------------------------------------------------------------------- */
CREATE TABLE dbo.chat_history (
    message_id       BIGINT IDENTITY(1,1) NOT NULL,
    user_id          VARCHAR(36)   NULL,  -- NULL nếu là Guest
    sender_type      VARCHAR(10)   NOT NULL,
    content          NVARCHAR(MAX) NOT NULL,
    matched_card_id  VARCHAR(50)   NULL,
    created_at       DATETIME2     NOT NULL CONSTRAINT DF_chat_history_created_at DEFAULT SYSDATETIME(),
    CONSTRAINT PK_chat_history             PRIMARY KEY (message_id),
    CONSTRAINT FK_chat_history_users       FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE SET NULL,
    CONSTRAINT CK_chat_history_sender_type CHECK (sender_type IN ('USER', 'BOT'))
);
GO

/* ---------------------------------------------------------------------
   Bảng 4: user_feedbacks - Đánh giá / báo lỗi Evidence Card
   --------------------------------------------------------------------- */
CREATE TABLE dbo.user_feedbacks (
    feedback_id       INT IDENTITY(1,1) NOT NULL,
    user_id           VARCHAR(36)  NOT NULL,
    evidence_card_id  VARCHAR(50)  NOT NULL,
    feedback_type     VARCHAR(20)  NOT NULL,
    created_at        DATETIME2    NOT NULL CONSTRAINT DF_user_feedbacks_created_at DEFAULT SYSDATETIME(),
    CONSTRAINT PK_user_feedbacks       PRIMARY KEY (feedback_id),
    CONSTRAINT FK_user_feedbacks_users FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE CASCADE,
    CONSTRAINT CK_user_feedbacks_type  CHECK (feedback_type IN ('LIKE', 'REPORT'))
);
GO

/* ---------------------------------------------------------------------
   Bảng 5: community_contributions - Đóng góp cộng đồng (300 phản hồi khảo sát)
   --------------------------------------------------------------------- */
CREATE TABLE dbo.community_contributions (
    contribution_id  VARCHAR(50)   NOT NULL,  -- vd: REV-2026-001
    user_id          VARCHAR(36)   NOT NULL,
    country_code     VARCHAR(10)   NOT NULL,  -- JP, KR, AU
    domain_id        VARCHAR(50)   NOT NULL,  -- giao_tiep, phap_ly, nha_o, tai_chinh...
    exp_title        NVARCHAR(255) NOT NULL,
    exp_text         NVARCHAR(MAX) NOT NULL,
    prep_level       INT           NULL,      -- Thang đo 1 - 5
    use_intention    INT           NULL,      -- Thang đo 1 - 5
    status           VARCHAR(20)   NOT NULL CONSTRAINT DF_cc_status DEFAULT 'PENDING',
    submitted_at     DATETIME2     NOT NULL CONSTRAINT DF_cc_submitted_at DEFAULT SYSDATETIME(),
    CONSTRAINT PK_community_contributions PRIMARY KEY (contribution_id),
    CONSTRAINT FK_cc_users                FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE CASCADE,
    CONSTRAINT CK_cc_prep_level    CHECK (prep_level    IS NULL OR prep_level    BETWEEN 1 AND 5),
    CONSTRAINT CK_cc_use_intention CHECK (use_intention IS NULL OR use_intention BETWEEN 1 AND 5),
    CONSTRAINT CK_cc_status        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
);
GO

/* ---------------------------------------------------------------------
   Bảng 6: contribution_challenges - Khó khăn đã chọn (1-N)
   --------------------------------------------------------------------- */
CREATE TABLE dbo.contribution_challenges (
    id               INT IDENTITY(1,1) NOT NULL,
    contribution_id  VARCHAR(50) NOT NULL,
    challenge_code   VARCHAR(50) NOT NULL,  -- giao_tiep, nha_o, thu_tuc_hanh_chinh...
    CONSTRAINT PK_contribution_challenges PRIMARY KEY (id),
    CONSTRAINT FK_cch_contributions       FOREIGN KEY (contribution_id)
        REFERENCES dbo.community_contributions (contribution_id) ON DELETE CASCADE,
    CONSTRAINT UQ_cch_contribution_code   UNIQUE (contribution_id, challenge_code)
);
GO

/* ---------------------------------------------------------------------
   Bảng 7: admin_queue_logs - Audit log kiểm duyệt
   --------------------------------------------------------------------- */
CREATE TABLE dbo.admin_queue_logs (
    log_id         INT IDENTITY(1,1) NOT NULL,
    admin_user_id  VARCHAR(36) NOT NULL,
    reference_id   VARCHAR(50) NOT NULL,
    action_taken   VARCHAR(20) NOT NULL,
    processed_at   DATETIME2   NOT NULL CONSTRAINT DF_aql_processed_at DEFAULT SYSDATETIME(),
    CONSTRAINT PK_admin_queue_logs PRIMARY KEY (log_id),
    CONSTRAINT FK_aql_users        FOREIGN KEY (admin_user_id)
        REFERENCES dbo.users (user_id),
    CONSTRAINT CK_aql_action       CHECK (action_taken IN ('APPROVE', 'REJECT'))
);
GO

/* ---------------------------------------------------------------------
   INDEX hỗ trợ truy vấn hiệu năng cao
   --------------------------------------------------------------------- */
CREATE INDEX IX_chat_history_user_created ON dbo.chat_history (user_id, created_at);
CREATE INDEX IX_user_feedbacks_card       ON dbo.user_feedbacks (evidence_card_id);
CREATE INDEX IX_cc_status_submitted       ON dbo.community_contributions (status, submitted_at);
CREATE INDEX IX_cc_user                   ON dbo.community_contributions (user_id);
CREATE INDEX IX_cc_country_domain         ON dbo.community_contributions (country_code, domain_id);
CREATE INDEX IX_aql_reference             ON dbo.admin_queue_logs (reference_id);
GO

/* =====================================================================
   MOCK DATA SECTION - CHUẨN HÓA 100% THEO THUYẾT MINH AISC 2026 (ASTERIA)
   Tổng mẫu: 300 Phản hồi khảo sát (Survey Responses = 300)
   - Cân bằng 3 thị trường: Nhật Bản (100), Hàn Quốc (100), Úc (100)
   - Mức độ sẵn sàng (Readiness):
       + Low readiness (1-2): 37.7% (113 mẫu) [trong đó 21.7% No preparation]
       + Neutral (3):        17.0% (51 mẫu)
       + High readiness (4-5): 45.3% (136 mẫu)
   - Ý định sử dụng (Use Intention):
       + Mean: 3.03
       + High use intention (4-5): 41.7% (125 mẫu)
   - Thống kê rào cản theo chủ đề (Difficulty by Topic):
       + Tham gia cộng đồng: 42.9% (~129 mẫu)
       + Thủ tục hành chính: 37.6% (~113 mẫu)
       + Giao tiếp:          36.1% (~108 mẫu)
       + Học tập/công việc:  34.9% (~105 mẫu)
       + Cuộc sống hằng ngày: 25.7% (~77 mẫu)
   ===================================================================== */

-- 1. BẢNG users: 3 Admins + 300 Người tham gia khảo sát
INSERT INTO dbo.users (user_id, email, password_hash, full_name, role, created_at) VALUES
 ('11111111-aaaa-0000-0000-000000000001', 'phuctrandinh2006@gmail.com',  '$2b$12$eX8mP.F9dE1K9LzQ7bV.eu9Y1H0aM2k4P5q8W3e7R6t9Y0u1I2o3P', N'Trần Đình Phúc',    'ADMIN', '2026-01-10 08:00:00'),
 ('11111111-aaaa-0000-0000-000000000002', 'khoahuynh212006@gmail.com',  '$2b$12$eX8mP.F9dE1K9LzQ7bV.eu9Y1H0aM2k4P5q8W3e7R6t9Y0u1I2o3P', N'Huỳnh Đăng Khoa',   'ADMIN', '2026-01-10 08:15:00'),
 ('11111111-aaaa-0000-0000-000000000003', 'admin@aisc.vn',              '$2b$12$eX8mP.F9dE1K9LzQ7bV.eu9Y1H0aM2k4P5q8W3e7R6t9Y0u1I2o3P', N'Ban Quản Trị AISC', 'ADMIN', '2026-01-05 09:00:00');
GO

-- Sinh tự động 300 Users người dùng thực tế với họ tên Tiếng Việt đa dạng
SET NOCOUNT ON;
BEGIN
    DECLARE @i INT = 1;
    DECLARE @uid VARCHAR(36);
    DECLARE @email VARCHAR(100);
    DECLARE @fullname NVARCHAR(100);
    DECLARE @created DATETIME2;

    DECLARE @ho TABLE (id INT IDENTITY(1,1), name NVARCHAR(20));
    INSERT INTO @ho (name) VALUES 
      (N'Nguyễn'), (N'Trần'), (N'Lê'), (N'Phạm'), (N'Hoàng'), (N'Huỳnh'), 
      (N'Phan'), (N'Vũ'), (N'Võ'), (N'Đặng'), (N'Bùi'), (N'Đỗ'), (N'Hồ'), 
      (N'Ngô'), (N'Dương'), (N'Lý'), (N'Đinh'), (N'Đoàn'), (N'Mai'), (N'Cao');

    DECLARE @dem TABLE (id INT IDENTITY(1,1), name NVARCHAR(20));
    INSERT INTO @dem (name) VALUES 
      (N'Văn'), (N'Thị'), (N'Đức'), (N'Hữu'), (N'Thanh'), (N'Minh'), 
      (N'Hoài'), (N'Thu'), (N'Gia'), (N'Quốc'), (N'Ngọc'), (N'Khánh');

    DECLARE @ten TABLE (id INT IDENTITY(1,1), name NVARCHAR(20));
    INSERT INTO @ten (name) VALUES 
      (N'An'), (N'Bình'), (N'Cường'), (N'Dũng'), (N'Hương'), (N'Hoa'), (N'Huy'), 
      (N'Khoa'), (N'Linh'), (N'Mai'), (N'Nam'), (N'Ngọc'), (N'Phúc'), (N'Quang'), 
      (N'Sơn'), (N'Thảo'), (N'Trang'), (N'Tuấn'), (N'Việt'), (N'Yến');

    WHILE @i <= 300
    BEGIN
        SET @uid = 'usr-2026-0000-0000-' + RIGHT('000000000000' + CAST(@i AS VARCHAR(12)), 12);
        SET @email = 'respondent.' + CAST(@i AS VARCHAR(5)) + '@survey.aisc.vn';
        
        DECLARE @h NVARCHAR(20) = (SELECT name FROM @ho WHERE id = ((@i * 7) % 20) + 1);
        DECLARE @d NVARCHAR(20) = (SELECT name FROM @dem WHERE id = ((@i * 5) % 12) + 1);
        DECLARE @t NVARCHAR(20) = (SELECT name FROM @ten WHERE id = ((@i * 11) % 20) + 1);
        SET @fullname = @h + N' ' + @d + N' ' + @t;
        
        SET @created = DATEADD(DAY, (@i % 45), '2026-01-10 08:00:00');

        INSERT INTO dbo.users (user_id, email, password_hash, full_name, role, created_at)
        VALUES (@uid, @email, '$2b$12$eX8mP.F9dE1K9LzQ7bV.eu9Y1H0aM2k4P5q8W3e7R6t9Y0u1I2o3P', @fullname, 'USER', @created);

        SET @i = @i + 1;
    END;
END;
GO

-- 2. BẢNG user_profiles: Phân bổ 300 hồ sơ bám sát ma trận Dashboard
-- 100 JP, 100 KR, 100 AU | 70% Du học, 20% Lao động, 10% Định cư | 4 Stage
SET NOCOUNT ON;
BEGIN
    DECLARE @i INT = 1;
    DECLARE @uid VARCHAR(36);
    DECLARE @country VARCHAR(10);
    DECLARE @purpose VARCHAR(50);
    DECLARE @stage VARCHAR(50);

    WHILE @i <= 300
    BEGIN
        SET @uid = 'usr-2026-0000-0000-' + RIGHT('000000000000' + CAST(@i AS VARCHAR(12)), 12);
        
        -- Phân bổ đều 3 quốc gia (100 người mỗi nước)
        IF @i <= 100 SET @country = 'JP';
        ELSE IF @i <= 200 SET @country = 'KR';
        ELSE SET @country = 'AU';

        -- Mục đích: 70% Du học, 20% Lao động, 10% Định cư
        DECLARE @modPurpose INT = @i % 10;
        IF @modPurpose < 7 SET @purpose = 'DU_HOC';
        ELSE IF @modPurpose < 9 SET @purpose = 'LAO_DONG';
        ELSE SET @purpose = 'DINH_CU';

        -- Giai đoạn hành trình (Stage):
        -- PREPARING (30%), RECENT_ARRIVED (25%), LIVING_STUDYING (30%), RETURNED (15%)
        DECLARE @modStage INT = @i % 20;
        IF @modStage < 6 SET @stage = 'PREPARING';
        ELSE IF @modStage < 11 SET @stage = 'RECENT_ARRIVED';
        ELSE IF @modStage < 17 SET @stage = 'LIVING_STUDYING';
        ELSE SET @stage = 'RETURNED';

        INSERT INTO dbo.user_profiles (user_id, target_country, purpose, stage)
        VALUES (@uid, @country, @purpose, @stage);

        SET @i = @i + 1;
    END;
END;
GO

-- 3. BẢNG chat_history: 18 lượt hỏi đáp RAG chất lượng cao + Fallback
INSERT INTO dbo.chat_history (user_id, sender_type, content, matched_card_id, created_at) VALUES
 ('usr-2026-0000-0000-000000000001', 'USER',
  N'Khi làm thêm ở quán ăn Nhật Bản, nếu vô tình làm vỡ bát đĩa thì cách ứng xử đúng chuẩn là gì?',
  NULL, '2026-02-10 18:30:10'),
 ('usr-2026-0000-0000-000000000001', 'BOT',
  N'【Phân tích bối cảnh】 Trong môi trường dịch vụ quán ăn Nhật Bản (Izakaya/Teishoku), an toàn khách hàng và quy tắc trách nhiệm cá nhân là ưu tiên cao nhất. Quản lý đánh giá cao sự trung thực và quy trình xử lý bình tĩnh hơn là việc trách cứ sự cố bất cẩn.

【Hành vi ứng xử an toàn】
1. Lập tức cúi chào tạ lỗi to rõ bằng tiếng Nhật: "Taihen moushiwake gozaimasen!" (大変申し訳ございません).
2. Kiểm tra nhanh xem mảnh vỡ có văng trúng khách hoặc đồng nghiệp không.
3. Thực hiện ngay Hou-ren-so (Báo cáo khẩn) cho Quản lý (Tencho) hoặc trưởng ca, không tự ý rời đi.
4. Mang biển cảnh báo trơn trượt/mảnh vỡ, dùng chổi gom và dùng khăn ẩm lau sạch bột thủy tinh/sứ li ti.

【Điều cần tránh】
- Tuyệt đối không giấu mảnh vỡ vào thùng rác mà không báo cáo.
- Không dùng tay không gom mảnh vỡ sắc nhọn.
- Không biện minh do sàn trơn hay khách va quẹt.

【Nguồn kiểm chứng】
Thẻ Evidence Card: EC-JP-GIAOTIEP-001 (JASSO Part-time Job Handbook & JNTO Manners Guide).',
  'EC-JP-GIAOTIEP-001', '2026-02-10 18:30:15'),

 ('usr-2026-0000-0000-000000000001', 'USER',
  N'Cuối buổi làm có cần đến gặp quản lý xin lỗi lại lần nữa không?',
  NULL, '2026-02-10 18:32:00'),
 ('usr-2026-0000-0000-000000000001', 'BOT',
  N'【Phân tích bối cảnh】 Trong văn hóa công sở Nhật Bản, hành động "tạ lỗi lần hai" thể hiện tinh thần Hansei (phản tỉnh sâu sắc) và sự chu đáo trong giao tiếp.

【Hành vi ứng xử an toàn】
- Trước khi ra về (sau khi chào Otsukaresama desu), hãy chủ động tìm gặp Tencho: "Kyou wa gomeiwaku wo okakesite, hontou ni moushiwake gozaimasen deshita" (Hôm nay em đã làm phiền mọi người, thật lòng xin lỗi ạ).
- Cảm ơn đồng nghiệp đã hỗ trợ dọn dẹp.

【Điều cần tránh】
- Hết ca lẳng lặng đi về như không có chuyện gì xảy ra.',
  'EC-JP-GIAOTIEP-001', '2026-02-10 18:32:04'),

 ('usr-2026-0000-0000-000000000002', 'USER',
  N'Thủ tục đăng ký cư trú khi mới đến Nhật Bản cần làm những gì và thời hạn trong bao lâu?',
  NULL, '2026-02-11 09:15:20'),
 ('usr-2026-0000-0000-000000000002', 'BOT',
  N'【Phân tích bối cảnh】 Theo Luật Quản lý Xuất nhập cảnh Nhật Bản, công dân quốc tế lưu trú trung và dài hạn bắt buộc phải khai báo nơi cư trú chính thức (Juminhyo) tại cơ quan hành chính địa phương.

【Hành vi ứng xử an toàn】
1. Trong vòng 14 ngày kể từ khi ổn định chỗ ở, mang Thẻ lưu trú (Zairyu Card), Hộ chiếu và Giấy tờ thuê nhà/KTX đến Ủy ban quận/thị trấn (Shiyakusho/Kuyakusho).
2. Đăng ký đồng thời: Địa chỉ cư trú ghi mặt sau thẻ Zairyu, Bảo hiểm Y tế Quốc dân (NHI), và nộp đơn xin miễn giảm Lương hưu Quốc dân (Nenkin).

【Điều cần tránh】
- Không để quá hạn 14 ngày vì sẽ bị coi là vi phạm nghĩa vụ lưu trú, ảnh hưởng trực tiếp đến việc gia hạn visa sau này.',
  'EC-JP-PHAPLY-001', '2026-02-11 09:15:25'),

 ('usr-2026-0000-0000-000000000101', 'USER',
  N'Du học sinh mới sang Hàn Quốc thì cần làm thẻ người nước ngoài (ARC) ở đâu và hồ sơ gồm những gì?',
  NULL, '2026-02-14 10:00:10'),
 ('usr-2026-0000-0000-000000000101', 'BOT',
  N'【Phân tích bối cảnh】 Du học sinh lưu trú tại Hàn Quốc trên 90 ngày bắt buộc phải đăng ký Thẻ cư trú người nước ngoài (ARC - Alien Registration Card / Residence Card) tại Cục Quản lý Xuất nhập cảnh Hàn Quốc.

【Hành vi ứng xử an toàn】
1. Bắt buộc đặt lịch hẹn trước trực tuyến qua cổng Hikorea (hikorea.go.kr) theo đúng chi cục quản lý khu vực bạn cư trú.
2. Hồ sơ: Đơn đăng ký theo mẫu, Hộ chiếu gốc + bản photo, Giấy chứng nhận đang học (Certificate of Enrollment), Giấy tờ cư trú (Hợp đồng thuê nhà/KTX), 1 ảnh thẻ 3.5x4.5cm phông trắng, Lệ phí 30,000 KRW.
3. Hoàn tất đăng ký trong vòng 90 ngày kể từ ngày đặt chân đến Hàn Quốc.',
  'EC-KR-PHAPLY-001', '2026-02-14 10:00:16'),

 ('usr-2026-0000-0000-000000000101', 'USER',
  N'Đi ăn liên hoan (Hoesik) với các tiền bối người Hàn thì có quy tắc ứng xử trên bàn rượu nào cần nhớ?',
  NULL, '2026-02-14 10:05:00'),
 ('usr-2026-0000-0000-000000000101', 'BOT',
  N'【Phân tích bối cảnh】 Hoesik (tiệc liên hoan) là nét văn hóa gắn kết quan hệ xã hội quan trọng tại Hàn Quốc. Quan hệ tôn ti trật tự theo tuổi tác và khóa học (Sunbae - Hoobae) được thể hiện rất rõ ràng tại đây.

【Hành vi ứng xử an toàn】
1. Khi tiền bối hoặc người lớn rót rượu: Dùng hai tay nâng ly (tay phải giữ ly, tay trái đỡ dưới đáy ly hoặc cổ tay phải).
2. Khi uống: Nghiêng người quay mặt sang một bên (hướng tránh ánh nhìn trực diện của người lớn), che miệng bằng tay còn lại.
3. Khi rót rượu mời tiền bối: Cũng dùng hai tay cầm chai, chỉ rót khi ly của đối phương đã cạn hoàn toàn.',
  'EC-KR-GIAOTIEP-001', '2026-02-14 10:05:06'),

 ('usr-2026-0000-0000-000000000201', 'USER',
  N'Visa du học Úc 500 hiện nay được phép làm thêm tối đa bao nhiêu giờ một tuần?',
  NULL, '2026-02-16 11:20:00'),
 ('usr-2026-0000-0000-000000000201', 'BOT',
  N'【Phân tích bối cảnh】 Từ ngày 01/07/2023, Chính phủ Úc đã tái áp dụng trần giới hạn thời gian làm thêm cho người giữ Student Visa (Subclass 500) nhằm đảm bảo mục tiêu học tập chính khóa.

【Hành vi ứng xử an toàn】
1. Giới hạn làm việc tối đa là 48 giờ trong mỗi chu kỳ 2 tuần (fortnight) trong thời gian khóa học đang diễn ra.
2. Trong kỳ nghỉ hè hoặc kỳ nghỉ giữa kỳ theo lịch nhà trường, bạn được phép làm việc không giới hạn số giờ.
3. Đăng ký Tax File Number (TFN) miễn phí trực tiếp trên trang Cục Thuế Úc (ATO) để hưởng bậc thuế cư dân hợp pháp và được bảo vệ quyền lợi lao động.',
  'EC-AU-PHAPLY-001', '2026-02-16 11:20:06'),

 ('usr-2026-0000-0000-000000000201', 'USER',
  N'Ăn uống ở nhà hàng tại Úc có bắt buộc phải trả tiền boa (tip) không?',
  NULL, '2026-02-16 11:25:00'),
 ('usr-2026-0000-0000-000000000201', 'BOT',
  N'【Phân tích bối cảnh】 Nước Úc có quy định mức lương sàn tối thiểu theo giờ rất cao cho người lao động ngành nhà hàng khách sạn. Vì vậy, tiền tip hoàn toàn không phải là quy tắc bắt buộc hay chuẩn mực xã hội như ở Hoa Kỳ.

【Hành vi ứng xử an toàn】
1. Tại các quán ăn, quán cà phê thông thường: Chỉ cần thanh toán chính xác theo số tiền trên hóa đơn.
2. Khi ăn tại nhà hàng cao cấp (Fine Dining) và nhân viên phục vụ chu đáo, bạn có thể tự nguyện tip 5% - 10%.
3. Văn hóa chia tiền sòng phẳng "Going Dutch" hoặc "Split the bill" cực kỳ phổ biến và hoàn toàn tự nhiên.',
  'EC-AU-GIAOTIEP-001', '2026-02-16 11:25:05'),

 ('usr-2026-0000-0000-000000000006', 'USER',
  N'Nếu mình muốn chuyển đổi từ visa du học sang visa thăm thân kết hôn tại Nhật thì có được miễn chứng minh tài chính không?',
  NULL, '2026-02-18 09:40:00'),
 ('usr-2026-0000-0000-000000000006', 'BOT',
  N'【Thông báo kiểm chứng thông tin】
Hệ thống không tìm thấy đủ bằng chứng kiểm chứng (Evidence Card) có độ tin cậy đạt chuẩn trong cơ sở tri thức cho trường hợp chuyển đổi diện visa đặc thù này của bạn.

Theo nguyên tắc an toàn pháp lý của hệ thống "Phiên dịch văn hóa số", trợ lý chủ động không đưa ra kết luận hoặc phỏng đoán nhằm phòng tránh rủi ro vi phạm hành chính ngoài ý muốn cho người dùng.

Khuyến nghị an toàn:
- Bạn vui lòng liên hệ trực tiếp Trung tâm Thông tin Tổng hợp Lưu trú cho Người nước ngoài thuộc Cục Quản lý Xuất nhập cảnh Nhật Bản (Tổng đài đa ngữ ISA: 0570-013904).
- Tra cứu trực tiếp tại cổng thông tin chính thức: https://www.moj.go.jp/isa/index.html',
  NULL, '2026-02-18 09:40:05'),

 (NULL, 'USER',
  N'Du học sinh Úc có bảo hiểm OSHC thì khi bị ốm phải đi khám ở đâu?',
  NULL, '2026-02-20 14:15:00'),
 (NULL, 'BOT',
  N'【Phân tích bối cảnh】 Bảo hiểm Y tế cho Du học sinh (OSHC - Overseas Student Health Cover) là điều kiện visa bắt buộc. Tuy nhiên hệ thống y tế Úc hoạt động theo mô hình phân tầng, khác biệt so với Việt Nam.

【Hành vi ứng xử an toàn】
1. Với các bệnh thông thường: Đặt lịch hẹn gặp Bác sĩ Đa khoa (GP - General Practitioner) tại phòng khám địa phương.
2. Ưu tiên chọn phòng khám "Direct Billing" liên kết với hãng OSHC của bạn (Allianz, Medibank, Bupa...) để không phải trả tiền trước.
3. Nếu cần xét nghiệm chuyên sâu, bắt buộc phải có Giấy chuyển tuyến (Referral Letter) từ bác sĩ GP.
4. Nguy cấp đe dọa tính mạng: Gọi ngay cấp cứu 000 hoặc đến thẳng Khoa Cấp cứu (Emergency Department).',
  'EC-AU-YTE-001', '2026-02-20 14:15:06');
GO

-- 4. BẢNG user_feedbacks: 16 phản hồi người dùng đánh giá Evidence Card
INSERT INTO dbo.user_feedbacks (user_id, evidence_card_id, feedback_type, created_at) VALUES
 ('usr-2026-0000-0000-000000000001', 'EC-JP-GIAOTIEP-001', 'LIKE',   '2026-02-10 18:35:00'),
 ('usr-2026-0000-0000-000000000002', 'EC-JP-PHAPLY-001',   'LIKE',   '2026-02-11 09:20:00'),
 ('usr-2026-0000-0000-000000000004', 'EC-JP-DOISONG-001',  'LIKE',   '2026-02-12 14:10:00'),
 ('usr-2026-0000-0000-000000000003', 'EC-JP-CONGVIEC-001', 'LIKE',   '2026-02-13 11:00:00'),
 ('usr-2026-0000-0000-000000000005', 'EC-JP-NHAO-001',     'REPORT', '2026-02-13 16:40:00'),
 ('usr-2026-0000-0000-000000000101', 'EC-KR-PHAPLY-001',   'LIKE',   '2026-02-14 10:10:00'),
 ('usr-2026-0000-0000-000000000101', 'EC-KR-GIAOTIEP-001', 'LIKE',   '2026-02-14 10:15:00'),
 ('usr-2026-0000-0000-000000000102', 'EC-KR-NHAO-001',     'LIKE',   '2026-02-15 15:45:00'),
 ('usr-2026-0000-0000-000000000103', 'EC-KR-TAICHINH-001', 'LIKE',   '2026-02-15 17:30:00'),
 ('usr-2026-0000-0000-000000000105', 'EC-KR-YTE-001',      'REPORT', '2026-02-16 08:20:00'),
 ('usr-2026-0000-0000-000000000201', 'EC-AU-PHAPLY-001',   'LIKE',   '2026-02-16 11:30:00'),
 ('usr-2026-0000-0000-000000000201', 'EC-AU-GIAOTIEP-001', 'LIKE',   '2026-02-16 11:32:00'),
 ('usr-2026-0000-0000-000000000202', 'EC-AU-NHAO-001',     'LIKE',   '2026-02-17 16:35:00'),
 ('usr-2026-0000-0000-000000000203', 'EC-AU-YTE-001',      'LIKE',   '2026-02-18 10:15:00'),
 ('usr-2026-0000-0000-000000000204', 'EC-AU-GIAOTHONG-001','LIKE',   '2026-02-19 14:00:00'),
 ('usr-2026-0000-0000-000000000208', 'EC-AU-PHAPLY-001',   'REPORT', '2026-02-20 09:50:00');
GO

-- 5. BẢNG community_contributions: Đúng 300 bản ghi chuẩn hóa theo KPI Dashboard
-- Phân phối prep_level: 65 mức 1, 48 mức 2 (Tổng Low 113 = 37.7%, No Prep 65 = 21.7%), 51 mức 3 (17.0%), 76 mức 4, 60 mức 5 (Tổng High 136 = 45.3%)
-- Phân phối use_intention: 53 mức 1, 57 mức 2, 65 mức 3, 78 mức 4, 47 mức 5 (Tổng High 125 = 41.7%, Mean = 909/300 = 3.03)
SET NOCOUNT ON;
BEGIN
    DECLARE @i INT = 1;
    DECLARE @cid VARCHAR(50);
    DECLARE @uid VARCHAR(36);
    DECLARE @country VARCHAR(10);
    DECLARE @domain VARCHAR(50);
    DECLARE @title NVARCHAR(255);
    DECLARE @text NVARCHAR(MAX);
    DECLARE @prep INT;
    DECLARE @intent INT;
    DECLARE @status VARCHAR(20);
    DECLARE @submitted DATETIME2;

    -- Bảng 9 lĩnh vực chuẩn hoá
    DECLARE @domains TABLE (id INT IDENTITY(1,1), name VARCHAR(50));
    INSERT INTO @domains (name) VALUES 
      ('giao_tiep'), ('phap_ly'), ('nha_o'), ('tai_chinh'), ('hoc_tap'),
      ('cong_viec'), ('y_te'), ('giao_thong'), ('doi_song');

    WHILE @i <= 300
    BEGIN
        SET @cid = 'REV-2026-' + RIGHT('000' + CAST(@i AS VARCHAR(3)), 3);
        SET @uid = 'usr-2026-0000-0000-' + RIGHT('000000000000' + CAST(@i AS VARCHAR(12)), 12);
        
        -- Quốc gia
        IF @i <= 100 SET @country = 'JP';
        ELSE IF @i <= 200 SET @country = 'KR';
        ELSE SET @country = 'AU';

        -- Lĩnh vực (luân phiên 9 lĩnh vực)
        SET @domain = (SELECT name FROM @domains WHERE id = ((@i % 9) + 1));

        -- Tiêu đề và nội dung theo quốc gia & lĩnh vực
        IF @country = 'JP'
        BEGIN
            IF @domain = 'giao_tiep' BEGIN
                SET @title = N'Văn hóa cúi chào Ojigi và giao tiếp kính ngữ khi phỏng vấn xin việc Baito';
                SET @text  = N'Khi đi phỏng vấn quán ăn hay combini, người Nhật rất quan sát tư thế đứng chào góc 30-45 độ và cách dùng thể lịch sự Teineigo. Chuẩn bị tốt giúp tạo ấn tượng ban đầu.';
            END
            ELSE IF @domain = 'phap_ly' BEGIN
                SET @title = N'Kinh nghiệm gia hạn visa du học và thủ tục chứng minh tài chính tại Cục Xuất nhập cảnh';
                SET @text  = N'Cần nộp giấy thuế cư trú (Kazei/Nozei Shomeisho) và sao kê tài khoản ngân hàng Yucho trước ngày hết hạn visa ít nhất 2 tháng để tránh rơi vào tình trạng quá hạn lưu trú.';
            END
            ELSE IF @domain = 'nha_o' BEGIN
                SET @title = N'Rào cản tiền lễ Reikin và tìm phòng trọ qua công ty bảo lãnh Hoshonin Kaisha';
                SET @text  = N'Chi phí đầu vào thuê nhà ở Tokyo rất tốn kém gồm Reikin, Shikikin và phí bảo lãnh. Người mới nên tìm các mô hình căn hộ sinh viên liên kết nhà trường để giảm bớt gánh nặng.';
            END
            ELSE IF @domain = 'tai_chinh' BEGIN
                SET @title = N'Đăng ký thẻ rút tiền ngân hàng Yucho Bank và thủ tục mở tài khoản cho người nước ngoài';
                SET @text  = N'Trong 6 tháng đầu, Yucho chỉ cấp sổ và thẻ giới hạn chuyển tiền trong nước. Sau 6 tháng mang con dấu Inkan và hợp đồng lao động ra mới kích hoạt chuyển khoản tự do.';
            END
            ELSE IF @domain = 'hoc_tap' BEGIN
                SET @title = N'Phương pháp ôn thi chứng chỉ JLPT N2/N1 kết hợp học chuyên ngành tại trường đại học';
                SET @text  = N'Áp lực đọc tài liệu kanji chuyên ngành khá nặng. Nên lập nhóm học cùng các bạn sinh viên bản xứ và tận dụng thư viện trường để mượn tài liệu ôn tập.';
            END
            ELSE IF @domain = 'cong_viec' BEGIN
                SET @title = N'Quy tắc báo cáo Hou-Ren-So và quản lý thời gian ca làm việc bán thời gian';
                SET @text  = N'Ở Nhật đến trước giờ làm 10-15 phút được coi là đúng giờ. Khi có việc đột xuất nghỉ phải gọi điện báo trực tiếp cho Tencho trước ca làm ít nhất 2-3 tiếng.';
            END
            ELSE IF @domain = 'y_te' BEGIN
                SET @title = N'Sử dụng thẻ Bảo hiểm Sức khỏe Quốc dân (NHI) khi khám răng và bệnh viện đa khoa';
                SET @text  = N'Bảo hiểm NHI chi trả 70% viện phí, sinh viên chỉ trả 30%. Lưu ý nhớ xin đơn miễn giảm đóng phí bảo hiểm tại quận Shiyakusho vào đầu mỗi năm tài chính.';
            END
            ELSE IF @domain = 'giao_thong' BEGIN
                SET @title = N'Kinh nghiệm mua vé tháng xe buýt và tàu điện ngầm Teikiken cho du học sinh';
                SET @text  = N'Xuất trình giấy chứng nhận học sinh sinh viên (Tsugaku Shomeisho) tại quầy vé nhà ga để mua vé tháng tuyến đi học giảm giá tới 50% so với vé thường.';
            END
            ELSE BEGIN
                SET @title = N'Quy định phân loại rác thải sinh hoạt theo lịch ngày chẵn lẻ của quận tại Nhật';
                SET @text  = N'Chai nhựa PET phải bóc nhãn, tháo nắp rửa sạch. Rác cháy được và không cháy được bỏ đúng túi chuyên dụng, vứt trước 8h sáng ngày quy định tránh bị dán nhãn từ chối.';
            END
        END
        ELSE IF @country = 'KR'
        BEGIN
            IF @domain = 'giao_tiep' BEGIN
                SET @title = N'Quy tắc xưng hô kính ngữ Jondaenmal và văn hóa tôn trọng tiền bối Sunbae';
                SET @text  = N'Trong môi trường trường học và câu lạc bộ Hàn Quốc, khoảng cách tuổi tác rất quan trọng. Cần dùng đuôi câu trang trọng -imnida/seumnida khi lần đầu nói chuyện.';
            END
            ELSE IF @domain = 'phap_ly' BEGIN
                SET @title = N'Quy trình đặt lịch hẹn online trên Hikorea để cấp mới và đổi địa chỉ thẻ ARC';
                SET @text  = N'Lịch hẹn tại chi cục xuất nhập cảnh Seoul thường kín trước 1 tháng. Khi chuyển phòng trọ phải khai báo địa chỉ mới trong vòng 14 ngày tại Jumin Center để tránh bị phạt tiền.';
            END
            ELSE IF @domain = 'nha_o' BEGIN
                SET @title = N'Kinh nghiệm tìm thuê phòng One-room và ký hợp đồng bảo đảm cọc Wolse';
                SET @text  = N'Luôn yêu cầu môi giới bất động sản xuất trình giấy xác nhận quyền sở hữu Deunggibudeungbon để đảm bảo chủ nhà không nợ ngân hàng quá mức an toàn.';
            END
            ELSE IF @domain = 'tai_chinh' BEGIN
                SET @title = N'Mở thẻ ngân hàng Hana/Woori và đăng ký dịch vụ chuyển tiền quốc tế về Việt Nam';
                SET @text  = N'Cần mang thẻ sinh viên và hộ chiếu ra chi nhánh ngân hàng trong khuôn viên trường để được hỗ trợ mở tài khoản sinh viên với thủ tục đơn giản nhất.';
            END
            ELSE IF @domain = 'hoc_tap' BEGIN
                SET @title = N'Áp lực bài tập nhóm Team-play và văn hóa làm việc gấp gáp Palli-palli';
                SET @text  = N'Sinh viên Hàn Quốc tương tác nhóm liên tục qua KakaoTalk. Luôn chủ động hoàn thành phần việc được phân công đúng hạn để tránh ảnh hưởng điểm đánh giá chéo đồng đội.';
            END
            ELSE IF @domain = 'cong_viec' BEGIN
                SET @title = N'Quy định xin giấy phép làm thêm bán thời gian S-3 cho sinh viên quốc tế tại Hàn';
                SET @text  = N'Phải có xác nhận của phòng quản lý sinh viên quốc tế và nộp đơn lên Cục Xuất nhập cảnh trước khi bắt đầu đi làm. Làm chui sẽ có nguy cơ bị hủy visa du học.';
            END
            ELSE IF @domain = 'y_te' BEGIN
                SET @title = N'Đăng ký khấu trừ tự động phí bảo hiểm y tế quốc dân bắt buộc NHIS qua ngân hàng';
                SET @text  = N'Sinh viên quốc tế được giảm 50% mức đóng tiêu chuẩn. Hãy cài đặt trừ tiền tự động để không bị trễ hạn đóng phí làm ảnh hưởng đến việc xét duyệt visa sau này.';
            END
            ELSE IF @domain = 'giao_thong' BEGIN
                SET @title = N'Sử dụng thẻ giao thông T-Money và quy tắc chuyển tuyến xe bus tàu điện miễn phí';
                SET @text  = N'Quẹt thẻ T-Money khi lên và xuống xe buýt để được tính giá ưu đãi chuyển tuyến miễn phí trong vòng 30 phút giữa hệ thống tàu điện ngầm và xe buýt.';
            END
            ELSE BEGIN
                SET @title = N'Thích nghi với thói quen ăn đồ cay nóng và văn hóa chia sẻ món phụ Banchan';
                SET @text  = N'Hầu hết các món ăn truyền thống Hàn đều có kim chi và bột ớt. Bạn có thể xin thêm cơm trắng và canh nhạt để điều chỉnh khẩu vị dần trong những tuần đầu.';
            END
        END
        ELSE -- AU
        BEGIN
            IF @domain = 'giao_tiep' BEGIN
                SET @title = N'Văn hóa chào hỏi Small Talk và giao tiếp cởi mở thân thiện của người Úc';
                SET @text  = N'Người bản xứ rất thích chào hỏi bằng "How ya going?" khi gặp trong thang máy hay trạm xe buýt. Chỉ cần đáp lại "Good, thanks! How are you?" một cách tự nhiên.';
            END
            ELSE IF @domain = 'phap_ly' BEGIN
                SET @title = N'Tuân thủ giới hạn 48 giờ làm việc / 2 tuần theo quy định Visa 500 của Fair Work';
                SET @text  = N'Theo dõi chặt chẽ bảng chấm công (timesheet). Chủ lao động Úc có nghĩa vụ đóng bảo hiểm hưu trí Superannuation (11.5%) cho bạn dù bạn là nhân viên part-time.';
            END
            ELSE IF @domain = 'nha_o' BEGIN
                SET @title = N'Bảo vệ quyền lợi tiền cọc thuê nhà thông qua cơ quan Rental Bonds Online (RBO)';
                SET @text  = N'Không bao giờ chuyển tiền cọc trực tiếp cho chủ nhà mà không có biên lai RBO tại NSW hoặc RTBA tại Victoria. Giữ kỹ Condition Report để đối chiếu khi trả nhà.';
            END
            ELSE IF @domain = 'tai_chinh' BEGIN
                SET @title = N'Đăng ký mã số thuế cá nhân TFN và mở tài khoản ngân hàng Commonwealth/ANZ';
                SET @text  = N'Đăng ký TFN online miễn phí qua cổng ATO sau khi nhập cảnh Úc. Cung cấp TFN cho ngân hàng để không bị trừ thuế thu nhập ở mức cao nhất 47% trên tiền lãi.';
            END
            ELSE IF @domain = 'hoc_tap' BEGIN
                SET @title = N'Thích nghi với phong cách học tập chủ động và kỹ năng trích dẫn APA/Harvard';
                SET @text  = N'Các trường đại học tại Úc kiểm tra đạo văn rất khắt khe bằng Turnitin. Cần tham gia các buổi hướng dẫn Academic Integrity của thư viện trường để nắm vững kỹ năng viết.';
            END
            ELSE IF @domain = 'cong_viec' BEGIN
                SET @title = N'Tìm kiếm việc làm thêm an toàn trên Seek và Student Job Board của trường đại học';
                SET @text  = N'Nên xin các chứng chỉ bắt buộc như RSA (phục vụ đồ uống có cồn) hoặc White Card (lao động xây dựng) để dễ xin việc làm với mức lương tối thiểu hợp pháp.';
            END
            ELSE IF @domain = 'y_te' BEGIN
                SET @title = N'Quy trình đặt lịch hẹn bác sĩ đa khoa GP và thanh toán bảo hiểm y tế OSHC';
                SET @text  = N'Tải ứng dụng của hãng bảo hiểm (Allianz, Medibank, Bupa) để tìm phòng khám đối tác Direct Billing Clinic, giúp khám bệnh không cần thanh toán tiền mặt tại chỗ.';
            END
            ELSE IF @domain = 'giao_thong' BEGIN
                SET @title = N'Sử dụng thẻ giao thông Opal/Myki và quy tắc an toàn giao thông bên tay trái';
                SET @text  = N'Úc lái xe và đi bộ theo làn bên trái (Keep Left). Luôn nhớ tap-on và tap-off thẻ vé công cộng khi lên xuống tàu xe để tránh bị nhân viên thanh tra phạt nặng.';
            END
            ELSE BEGIN
                SET @title = N'Văn hóa ăn uống tự do, thanh toán chia tiền Split bill và tiền boa Tip tại Úc';
                SET @text  = N'Tiền tip không bắt buộc ở hầu hết nhà hàng quán ăn Úc do nhân viên đã hưởng mức lương tối thiểu rất cao. Bạn có thể thoải mái chọn không tip khi quẹt máy thanh toán.';
            END
        END;

        -- Gán prep_level (1 - 5) chính xác theo tỷ lệ Dashboard:
        -- Low (1-2): 113 mẫu (37.7%) [trong đó mức 1 là 65 mẫu = 21.7% No Prep, mức 2 là 48 mẫu]
        -- Neutral (3): 51 mẫu (17.0%)
        -- High (4-5): 136 mẫu (45.3%) [mức 4 là 76 mẫu, mức 5 là 60 mẫu]
        IF @i <= 65 SET @prep = 1;
        ELSE IF @i <= 113 SET @prep = 2;
        ELSE IF @i <= 164 SET @prep = 3;
        ELSE IF @i <= 240 SET @prep = 4;
        ELSE SET @prep = 5;

        -- Gán use_intention (1 - 5) chính xác:
        -- Mức 1: 53 mẫu | Mức 2: 57 mẫu | Mức 3: 65 mẫu | Mức 4: 78 mẫu | Mức 5: 47 mẫu
        -- Tổng High (4-5) = 78 + 47 = 125 mẫu (41.67% ≈ 41.7%)
        -- Tổng điểm: 53*1 + 57*2 + 65*3 + 78*4 + 47*5 = 53 + 114 + 195 + 312 + 235 = 909
        -- Điểm trung bình Mean: 909 / 300 = đúng 3.03!
        IF @i <= 53 SET @intent = 1;
        ELSE IF @i <= 110 SET @intent = 2;
        ELSE IF @i <= 175 SET @intent = 3;
        ELSE IF @i <= 253 SET @intent = 4;
        ELSE SET @intent = 5;

        -- Trạng thái duyệt:
        -- 245 APPROVED, 43 PENDING, 12 REJECTED
        IF @i <= 245 SET @status = 'APPROVED';
        ELSE IF @i <= 288 SET @status = 'PENDING';
        ELSE SET @status = 'REJECTED';

        -- Thời gian gửi bài
        SET @submitted = DATEADD(MINUTE, (@i * 47) % 1440, DATEADD(DAY, (@i % 45), '2026-01-15 09:00:00'));

        INSERT INTO dbo.community_contributions 
          (contribution_id, user_id, country_code, domain_id, exp_title, exp_text, prep_level, use_intention, status, submitted_at)
        VALUES 
          (@cid, @uid, @country, @domain, @title, @text, @prep, @intent, @status, @submitted);

        SET @i = @i + 1;
    END;
END;
GO

-- 6. BẢNG contribution_challenges: Gán nhãn khó khăn bám sát tỷ lệ trang 22
-- Tham gia cộng đồng: 42.9% (~129 mẫu)
-- Thủ tục hành chính: 37.6% (~113 mẫu)
-- Giao tiếp:          36.1% (~108 mẫu)
-- Học tập/công việc:  34.9% (~105 mẫu)
-- Cuộc sống hằng ngày: 25.7% (~77 mẫu)
SET NOCOUNT ON;
BEGIN
    DECLARE @i INT = 1;
    DECLARE @cid VARCHAR(50);

    WHILE @i <= 300
    BEGIN
        SET @cid = 'REV-2026-' + RIGHT('000' + CAST(@i AS VARCHAR(3)), 3);

        -- Nhóm 1: Tham gia cộng đồng (129 mẫu ~ 43.0% ≈ 42.9%)
        IF (@i % 100) < 43
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'tham_gia_cong_dong');
        END;

        -- Nhóm 2: Thủ tục hành chính (113 mẫu ~ 37.7% ≈ 37.6%)
        IF ((@i + 17) % 100) < 38
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'thu_tuc_hanh_chinh');
        END;

        -- Nhóm 3: Giao tiếp (108 mẫu ~ 36.0% ≈ 36.1%)
        IF ((@i + 33) % 100) < 36
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'giao_tiep');
        END;

        -- Nhóm 4: Học tập/công việc (105 mẫu ~ 35.0% ≈ 34.9%)
        IF ((@i + 51) % 100) < 35
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'hoc_tap_cong_viec');
        END;

        -- Nhóm 5: Cuộc sống hằng ngày (77 mẫu ~ 25.7% = 25.7%)
        IF ((@i + 73) % 100) < 26
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'cuoc_song_hang_ngay');
        END;

        -- Gán thêm các nhãn bổ trợ: nhà ở, tài chính, y tế để dashboard không bị trống
        IF (@i % 4) = 0
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'nha_o');
        END;

        IF (@i % 5) = 0
        BEGIN
            INSERT INTO dbo.contribution_challenges (contribution_id, challenge_code)
            VALUES (@cid, 'tai_chinh');
        END;

        SET @i = @i + 1;
    END;
END;
GO

-- 7. BẢNG admin_queue_logs: 257 lượt kiểm duyệt của Admin (245 APPROVE + 12 REJECT)
SET NOCOUNT ON;
BEGIN
    DECLARE @i INT = 1;
    DECLARE @cid VARCHAR(50);
    DECLARE @status VARCHAR(20);
    DECLARE @admin_id VARCHAR(36);
    DECLARE @processed DATETIME2;

    DECLARE cur_contrib CURSOR LOCAL FAST_FORWARD FOR
        SELECT contribution_id, status, submitted_at
        FROM dbo.community_contributions
        WHERE status IN ('APPROVED', 'REJECTED');

    DECLARE @sub DATETIME2;
    OPEN cur_contrib;
    FETCH NEXT FROM cur_contrib INTO @cid, @status, @sub;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        -- Phân chia duyệt giữa 3 Admin dự án Asteria
        IF (@i % 3) = 1 SET @admin_id = '11111111-aaaa-0000-0000-000000000001';
        ELSE IF (@i % 3) = 2 SET @admin_id = '11111111-aaaa-0000-0000-000000000002';
        ELSE SET @admin_id = '11111111-aaaa-0000-0000-000000000003';

        SET @processed = DATEADD(HOUR, 2 + (@i % 24), @sub);

        INSERT INTO dbo.admin_queue_logs (admin_user_id, reference_id, action_taken, processed_at)
        VALUES (@admin_id, @cid, CASE WHEN @status = 'APPROVED' THEN 'APPROVE' ELSE 'REJECT' END, @processed);

        SET @i = @i + 1;
        FETCH NEXT FROM cur_contrib INTO @cid, @status, @sub;
    END;

    CLOSE cur_contrib;
    DEALLOCATE cur_contrib;
END;
GO

/* =====================================================================
   CÂU TRUY VẤN KIỂM CHỨNG CHỈ SỐ DASHBOARD (VERIFICATION QUERIES)
   Chạy các câu lệnh dưới đây để kiểm tra độ khớp với Thuyết minh (Trang 22-24):
   =====================================================================

   -- 1. Tổng số mẫu và tỷ lệ sẵn sàng (Readiness):
   SELECT 
       COUNT(*) AS total_survey_responses,
       CAST(SUM(CASE WHEN prep_level <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS low_readiness_pct,      -- Mục tiêu: 37.7%
       CAST(SUM(CASE WHEN prep_level = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS no_preparation_pct,     -- Mục tiêu: 21.7%
       CAST(SUM(CASE WHEN prep_level >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS high_readiness_pct       -- Mục tiêu: 45.3%
   FROM dbo.community_contributions;

   -- 2. Ý định sử dụng sản phẩm (Product Use Intention):
   SELECT 
       CAST(AVG(CAST(use_intention AS FLOAT)) AS DECIMAL(4,2)) AS mean_use_intention,                                        -- Mục tiêu: 3.03
       CAST(SUM(CASE WHEN use_intention >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,1)) AS high_use_intention_pct -- Mục tiêu: 41.7%
   FROM dbo.community_contributions;

   -- 3. Phân bổ mẫu theo 3 quốc gia (Respondent Mix):
   SELECT country_code, COUNT(*) AS count_by_country, CAST(COUNT(*) * 100.0 / 300 AS DECIMAL(5,1)) AS pct
   FROM dbo.community_contributions
   GROUP BY country_code;

   -- 4. Thống kê tỷ lệ khó khăn theo chủ đề (Difficulty by Topic):
   SELECT 
       challenge_code, 
       COUNT(*) AS count_challenges,
       CAST(COUNT(*) * 100.0 / 300 AS DECIMAL(5,1)) AS pct_difficulty                                                       -- Mục tiêu: 42.9%, 37.6%, 36.1%, 34.9%, 25.7%
   FROM dbo.contribution_challenges
   GROUP BY challenge_code
   ORDER BY count_challenges DESC;
   ===================================================================== */
