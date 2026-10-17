/**
 * DATA MODEL & MOCK DATABASE FOR "PHIÊN DỊCH VĂN HOÁ SỐ" (DIGITAL CULTURAL INTERPRETER)
 * AISC'26 - Team Asteria (UIT - ĐHQG TP.HCM)
 * 9 Standardized Life Domains, Evidence Cards, Benchmarks & Survey Metrics
 */

const APP_DATA = {
  projectInfo: {
    nameVi: "Phiên Dịch Văn Hoá Số",
    nameEn: "Digital Cultural Interpreter",
    contest: "Advanced Information Systems Contest 2026 (AISC'26)",
    track: "Data-Driven Business - Social Tech",
    team: "Asteria",
    university: "Trường Đại học Công nghệ Thông tin – ĐHQG TP.HCM",
    members: [
      { name: "Trần Đình Phúc", role: "Trưởng nhóm", mssv: "24521397" },
      { name: "Huỳnh Đăng Khoa", role: "Thành viên", mssv: "24522074" },
      { name: "Nguyễn Hoài Nam", role: "Thành viên", mssv: "24521109" },
      { name: "Nguyễn Triệu Hoàng", role: "Thành viên", mssv: "23520534" },
      { name: "Đặng Trúc Mai", role: "Thành viên", mssv: "24521037" }
    ]
  },

  // Chuẩn hóa 9 lĩnh vực đời sống cố định theo đề án
  domains: [
    {
      id: "phap_ly",
      code: "DOM-01",
      name: "Hành chính – Pháp lý",
      icon: "scale",
      color: "var(--accent-primary)",
      desc: "Thủ tục visa, thẻ cư trú, đăng ký thường trú, lao động, hợp đồng và quyền công dân."
    },
    {
      id: "cong_viec",
      code: "DOM-02",
      name: "Học tập – Công việc",
      icon: "briefcase",
      color: "var(--accent-ochre)",
      desc: "Văn hóa công sở, làm thêm (baito), thi cử, đạo đức học thuật và quan hệ cấp trên - cấp dưới."
    },
    {
      id: "giao_tiep",
      code: "DOM-03",
      name: "Giao tiếp – Văn hoá ứng xử",
      icon: "message-circle",
      color: "var(--accent-ocean)",
      desc: "Kính ngữ, cúi chào, xưng hô, giao tiếp phi ngôn ngữ, văn hóa xin lỗi và thể diện."
    },
    {
      id: "nha_o",
      code: "DOM-04",
      name: "Nhà ở – Tiện ích",
      icon: "home",
      color: "var(--accent-forest)",
      desc: "Thuê nhà, tiền lễ (Reikin/Shikikin), phân loại rác, tiếng ồn và nội quy căn hộ."
    },
    {
      id: "tai_chinh",
      code: "DOM-05",
      name: "Tài chính – Ngân hàng",
      icon: "credit-card",
      color: "var(--accent-ochre)",
      desc: "Mở tài khoản ngân hàng, chuyển tiền kiều hối, mã số thuế và thanh toán điện tử."
    },
    {
      id: "y_te",
      code: "DOM-06",
      name: "Y tế – Bảo hiểm",
      icon: "activity",
      color: "var(--accent-forest)",
      desc: "Bảo hiểm y tế quốc dân (Kokumin Kenko Hoken / NHIS / OSHC), khám chữa bệnh và cấp cứu."
    },
    {
      id: "giao_thong",
      code: "DOM-07",
      name: "Giao thông – Đi lại",
      icon: "map-pin",
      color: "var(--accent-ocean)",
      desc: "Tàu điện, xe buýt, thẻ IC/Opal, văn hóa nhường ghế, quy định đi xe đạp và bằng lái."
    },
    {
      id: "doi_song",
      code: "DOM-08",
      name: "Đời sống hằng ngày – Ẩm thực",
      icon: "coffee",
      color: "var(--accent-forest)",
      desc: "Quy chuẩn bàn ăn, rót rượu, tiền tip, chia hóa đơn (betsu-betsu / Dutch treat), siêu thị."
    },
    {
      id: "cong_dong",
      code: "DOM-09",
      name: "Cộng đồng – Mạng lưới hỗ trợ",
      icon: "users",
      color: "var(--accent-ocean)",
      desc: "Hội đồng hương, hỗ trợ sinh viên quốc tế, cơ quan đại diện ngoại giao và các tổ chức thiện nguyện."
    }
  ],

  // Danh mục quốc gia hỗ trợ
  countries: [
    { id: "JP", name: "Nhật Bản", flag: "", code: "Japan", currency: "JPY", expatEstimate: "500,000+" },
    { id: "KR", name: "Hàn Quốc", flag: "", code: "South Korea", currency: "KRW", expatEstimate: "250,000+" },
    { id: "AU", name: "Australia", flag: "", code: "Australia", currency: "AUD", expatEstimate: "350,000+" }
  ],

  // Quản lý vai trò (User Role & Permissions)
  roles: [
    { id: "GUEST", name: "Khách (Chưa đăng nhập)", badge: "Khách", desc: "Tra cứu thông tin và hỏi đáp AI cơ bản" },
    { id: "USER", name: "Người dùng (Đã đăng nhập)", badge: "Thành viên", desc: "Được phép đóng góp dữ liệu, khảo sát và cá nhân hóa" },
    { id: "ADMIN", name: "Quản trị viên (Admin)", badge: "Admin", desc: "Toàn quyền quản trị hàng đợi duyệt, master data và xem báo cáo thống kê" }
  ],

  // Cơ sở dữ liệu Evidence Card mẫu đã kiểm chứng
  evidenceCards: [
    {
      id: "EVD-JP-001",
      country: "JP",
      countryName: "Nhật Bản",
      domainId: "cong_viec",
      domainName: "Học tập – Công việc",
      title: "Ứng xử chuẩn khi vô tình làm vỡ bát đĩa tại nơi làm thêm (Baito)",
      context: "Du học sinh làm thêm tại nhà hàng, quán ăn (Izakaya, Ramen) vô tình làm vỡ dụng cụ.",
      verifiedContent: "Theo quy chuẩn văn hóa công sở Nhật Bản (Horenso: Hokoku - Renraku - Sodan), khi xảy ra sự cố, người lao động phải lập tức báo cáo trực tiếp cho Tencho (Quản lý) hoặc người phụ trách ca trước tiên.",
      safeAction: "Nói to rõ ràng lời xin lỗi: 'Moushiwake gozaimasen' (申し訳ございません) hoặc 'Taihen shitsurei itashimashita'. Hỏi ý kiến quản lý cách xử lý mảnh vỡ để đảm bảo an toàn cho khách, không tự ý dọn một mình nếu chưa báo.",
      donots: "Tuyệt đối không giấu mảnh vỡ vào thùng rác khuất, không tự ý bỏ qua hoặc tranh cãi đổ lỗi cho khách hay đồng nghiệp.",
      organization: "JASSO & Cẩm nang Horenso Quán ăn Nhật Bản",
      sourceType: "Chính thống / Tổ chức chính phủ",
      sourceUrl: "https://www.studyinjapan.go.jp/ja/statistics/daily-life/data/2410311100.html",
      reliabilityScore: 98,
      confidenceLevel: "Rất cao (98%)",
      publishedDate: "2023-11-15",
      verifiedDate: "2024-02-10",
      status: "APPROVED"
    },
    {
      id: "EVD-JP-002",
      country: "JP",
      countryName: "Nhật Bản",
      domainId: "phap_ly",
      domainName: "Hành chính – Pháp lý",
      title: "Đăng ký cư trú và quy định giờ làm thêm 28 giờ/tuần đối với du học sinh",
      context: "Du học sinh mới nhập cảnh tại sân bay Narita/Haneda/Kansai.",
      verifiedContent: "Theo Đạo luật Kiểm soát Xuất nhập cảnh Nhật Bản (ISA), du học sinh phải đăng ký cư trú tại Shiyakusho/Kuyakusho trong vòng 14 ngày kể từ khi có địa chỉ cố định. Giấy phép làm thêm (Shikakugai Katsudo Kyoka) cho phép tối đa 28 giờ/tuần trong kỳ học và 8 giờ/ngày trong kỳ nghỉ dài.",
      safeAction: "Mang Hộ chiếu, Thẻ lưu trú (Zairyu Card) và hợp đồng thuê nhà tới Tòa thị chính (Kuyakusho) trong 14 ngày. Theo dõi bảng chấm công chặt chẽ không vượt quá 28h/tuần để tránh bị từ chối gia hạn visa.",
      donots: "Không làm việc tại các cơ sở giải trí người lớn (Fuzoku), pachinko, quán bar dù chỉ rửa bát dọn dẹp vì sẽ bị trục xuất ngay lập tức.",
      organization: "Cục Quản lý Xuất nhập cảnh Nhật Bản (ISA)",
      sourceType: "Cơ quan pháp lý chính phủ",
      sourceUrl: "https://www.isa.go.jp/en/applications/guide/tetuduki_index1.html",
      reliabilityScore: 99,
      confidenceLevel: "Rất cao (99%)",
      publishedDate: "2024-01-05",
      verifiedDate: "2024-03-01",
      status: "APPROVED"
    },
    {
      id: "EVD-JP-003",
      country: "JP",
      countryName: "Nhật Bản",
      domainId: "nha_o",
      domainName: "Nhà ở – Tiện ích",
      title: "Quy chuẩn phân loại rác và ứng xử tiếng ồn trong căn hộ chung cư (Apāto)",
      context: "Thuê nhà trọ hoặc căn hộ riêng tại các thành phố Nhật Bản.",
      verifiedContent: "Nhật Bản có lịch trình thu gom rác cực kỳ nghiêm ngặt chia theo ngày: Rác cháy được (Moeru Gomi), Rác không cháy được (Moenai Gomi), Rác tài nguyên (nhựa Pet, lon nhôm, giấy báo). Tường nhà apāto thường cách âm kém.",
      safeAction: "Dán lịch thu gom rác của Quận trước cửa tủ lạnh. Rửa sạch chai nhựa, bóc nhãn nylon trước khi bỏ vào thùng. Đi lại nhẹ nhàng và đeo tai nghe sau 21h00 tối.",
      donots: "Không vứt rác sai ngày hoặc vứt trước cửa hàng xóm. Không tụ tập ăn nhậu ồn ào vào ban đêm gây ảnh hưởng khiến cảnh sát hoặc công ty quản lý nhà can thiệp.",
      organization: "Cục Môi trường Đô thị Tokyo & Guidebook Đa ngữ ISA",
      sourceType: "Chính quyền đô thị",
      sourceUrl: "https://www.studyinjapan.go.jp/ja/statistics/daily-life/",
      reliabilityScore: 97,
      confidenceLevel: "Cao (97%)",
      publishedDate: "2023-09-20",
      verifiedDate: "2024-01-15",
      status: "APPROVED"
    },
    {
      id: "EVD-KR-001",
      country: "KR",
      countryName: "Hàn Quốc",
      domainId: "giao_tiep",
      domainName: "Giao tiếp – Văn hoá ứng xử",
      title: "Văn hóa kính ngữ, cúi chào và đưa nhận đồ bằng hai tay với tiền bối (Sunbae)",
      context: "Giao tiếp trong trường đại học, ký túc xá hoặc chỗ làm thêm tại Hàn Quốc.",
      verifiedContent: "Văn hóa Khổng giáo tại Hàn Quốc đặc biệt coi trọng tôn ti trật tự và tuổi tác. Khi giao tiếp với người lớn tuổi hơn hoặc tiền bối khóa trên, việc dùng kính ngữ (Jondaemal - 존댓말) và đưa/nhận đồ vật bằng hai tay là nguyên tắc tối thiểu.",
      safeAction: "Khi nhận tài liệu, danh thiếp hoặc rót đồ uống, hãy dùng hai tay (hoặc tay phải cầm, tay trái đỡ nhẹ dưới cẳng tay/cổ tay phải). Cúi chào góc 30-45 độ khi gặp giáo sư và tiền bối.",
      donots: "Không gọi tên trống không với người lớn tuổi hơn. Không tự ý nói 반말 (Banmal - nói ngang hàng) nếu đối phương chưa chính thức đề nghị.",
      organization: "Cultural Atlas – South Korean Etiquette & Bộ Ngoại giao Hàn Quốc (MOFA)",
      sourceType: "Tài liệu Văn hóa chuẩn quốc tế",
      sourceUrl: "https://culturalatlas.sbs.com.au/south-korean-culture/south-korean-culture-etiquette",
      reliabilityScore: 96,
      confidenceLevel: "Rất cao (96%)",
      publishedDate: "2023-10-12",
      verifiedDate: "2024-02-20",
      status: "APPROVED"
    },
    {
      id: "EVD-KR-002",
      country: "KR",
      countryName: "Hàn Quốc",
      domainId: "doi_song",
      domainName: "Đời sống hằng ngày – Ẩm thực",
      title: "Quy chuẩn bàn ăn và văn hóa dùng bữa cùng người Hàn Quốc (Hoesik / Bàn ăn)",
      context: "Đi ăn uống cùng giáo sư, đồng nghiệp, tiền bối hoặc bạn bè Hàn Quốc.",
      verifiedContent: "Theo phép lịch sự bàn ăn Hàn Quốc, người trẻ nhất hoặc hậu bối thường là người xếp đũa thìa, lấy khăn ướt và rót nước cho mọi người trước bữa ăn. Không nâng đũa trước khi người lớn tuổi nhất bắt đầu.",
      safeAction: "Chờ người lớn tuổi nhất nâng thìa/đũa mới bắt đầu ăn. Khi được người lớn rót rượu Soju, cầm ly bằng hai tay và hơi quay người sang hướng khác khi uống.",
      donots: "Không cắm thẳng đũa vào bát cơm (tập tục cúng viếng). Không cầm bát cơm đưa lên miệng như ở Việt Nam mà dùng thìa để múc.",
      organization: "Korea MOFA – Living in Korea & Study in Korea",
      sourceType: "Cổng thông tin chính phủ Hàn Quốc",
      sourceUrl: "https://mods.go.kr/board.es?act=view&bid=11109",
      reliabilityScore: 95,
      confidenceLevel: "Cao (95%)",
      publishedDate: "2023-08-14",
      verifiedDate: "2024-01-25",
      status: "APPROVED"
    },
    {
      id: "EVD-KR-003",
      country: "KR",
      countryName: "Hàn Quốc",
      domainId: "y_te",
      domainName: "Y tế – Bảo hiểm",
      title: "Quy định Bảo hiểm Y tế Quốc dân bắt buộc (NHIS) cho du học sinh quốc tế",
      context: "Sinh viên nước ngoài lưu trú trên 6 tháng tại Hàn Quốc.",
      verifiedContent: "Từ tháng 3/2021, tất cả du học sinh quốc tế diện visa D-2, D-4 tự động được đăng ký vào Bảo hiểm Y tế Quốc dân (NHIS) sau khi hoàn tất đăng ký Thẻ cư trú người nước ngoài (ARC).",
      safeAction: "Đóng phí bảo hiểm hàng tháng đúng hạn theo giấy báo gửi về địa chỉ cư trú để đảm bảo hưởng mức chi trả 50-80% viện phí khi ốm đau.",
      donots: "Không trốn đóng phí bảo hiểm, vì nợ phí trên 3 tháng sẽ bị hạn chế gia hạn visa và bị từ chối xuất cảnh tại sân bay.",
      organization: "National Health Insurance Service (NHIS) Hàn Quốc",
      sourceType: "Cơ quan bảo hiểm nhà nước",
      sourceUrl: "https://www.nhis.or.kr",
      reliabilityScore: 99,
      confidenceLevel: "Tuyệt đối (99%)",
      publishedDate: "2024-01-10",
      verifiedDate: "2024-02-15",
      status: "APPROVED"
    },
    {
      id: "EVD-AU-001",
      country: "AU",
      countryName: "Australia (Úc)",
      domainId: "cong_viec",
      domainName: "Học tập – Công việc",
      title: "Quyền lợi làm việc của sinh viên (Visa 500) và Mức lương tối thiểu theo luật Fair Work",
      context: "Du học sinh tìm việc làm thêm (Hospitality, Retail, Nông trại) tại Úc.",
      verifiedContent: "Theo Fair Work Ombudsman và Bộ Nội vụ Úc (Home Affairs), du học sinh visa 500 được làm tối đa 48 giờ/2 tuần trong kỳ học. Người lao động được hưởng mức lương tối thiểu (National Minimum Wage) hợp pháp, hiện tại là từ 23.23 AUD/giờ (cộng phụ cấp ca đêm/cuối tuần).",
      safeAction: "Yêu cầu chủ lao động trả lương qua tài khoản ngân hàng và cung cấp Payslip (phiếu lương). Tự khai mã số thuế (TFN) để tránh bị khấu trừ thuế suất tối đa 45%.",
      donots: "Không nhận lương tiền mặt dưới mức tối thiểu (Cash-in-hand bất hợp pháp), không đồng ý làm quá số giờ quy định dẫn đến nguy cơ bị hủy visa.",
      organization: "Fair Work Ombudsman – Cơ quan Bảo vệ Quyền lợi Lao động Úc",
      sourceType: "Cơ quan hành pháp chính phủ Úc",
      sourceUrl: "https://www.fairwork.gov.au/language-help/vietnamese",
      reliabilityScore: 99,
      confidenceLevel: "Rất cao (99%)",
      publishedDate: "2024-02-01",
      verifiedDate: "2024-03-05",
      status: "APPROVED"
    },
    {
      id: "EVD-AU-002",
      country: "AU",
      countryName: "Australia (Úc)",
      domainId: "giao_tiep",
      domainName: "Giao tiếp – Văn hoá ứng xử",
      title: "Văn hóa bình đẳng (Egalitarianism), Small Talk và cách xưng hô First Name ở Úc",
      context: "Giao tiếp hàng ngày, tại trường đại học hoặc nơi làm việc tại Úc.",
      verifiedContent: "Văn hóa Úc rất đề cao sự bình đẳng (No worries, Mate!). Học sinh thường gọi giáo sư bằng tên riêng (First Name) một cách thân thiện nhưng vẫn tôn trọng. Small talk (nói chuyện ngắn về thời tiết, thể thao) là chìa khóa hòa nhập xã hội.",
      safeAction: "Bắt đầu câu chuyện bằng 'How's it going?' hoặc 'Good morning'. Cảm ơn tài xế xe buýt khi bước xuống cửa sau ('Thank you, driver'). Xếp hàng (Queueing) kiên nhẫn tại bến xe và quầy thanh toán.",
      donots: "Không chen ngang hàng ngũ, không quá khép nép hay quá tự ti về vốn tiếng Anh vì người bản xứ rất cởi mở với người nói tiếng Anh như ngôn ngữ thứ hai.",
      organization: "Australian Government – AUSCO (Orientation Guidebook) & Cultural Atlas",
      sourceType: "Tài liệu Định hướng của Bộ Nội vụ Úc",
      sourceUrl: "https://culturalatlas.sbs.com.au/australian-culture",
      reliabilityScore: 96,
      confidenceLevel: "Cao (96%)",
      publishedDate: "2023-11-08",
      verifiedDate: "2024-01-18",
      status: "APPROVED"
    },
    {
      id: "EVD-AU-003",
      country: "AU",
      countryName: "Australia (Úc)",
      domainId: "doi_song",
      domainName: "Đời sống hằng ngày – Ẩm thực",
      title: "Quy ước tiền tip (Tipping) và chia hóa đơn (Splitting the bill) tại Úc",
      context: "Ăn uống tại nhà hàng, quán cà phê hoặc đi ăn theo nhóm tại Úc.",
      verifiedContent: "Tại Úc, tiền tip KHÔNG bắt buộc vì nhân viên phục vụ đã được trả mức lương tối thiểu thỏa đáng theo đạo luật Fair Work. Khi đi ăn nhóm, văn hóa chia đều hóa đơn (Split the bill) rất phổ biến và hoàn toàn tự nhiên.",
      safeAction: "Tự tin thanh toán đúng số tiền trên hóa đơn. Nếu dịch vụ thực sự xuất sắc, bạn có thể tip 5-10% hoặc làm tròn số tiền lẻ. Khi thanh toán tại quầy, có thể yêu cầu 'Can we split the bill please?'.",
      donots: "Không cảm thấy áp lực phải tip như ở Mỹ. Đừng ngại chia tiền sòng phẳng giữa bạn bè vì đó là phong cách văn hóa tiêu chuẩn.",
      organization: "Cultural Atlas – Australian Etiquette",
      sourceType: "Nghiên cứu văn hóa ứng xử",
      sourceUrl: "https://culturalatlas.sbs.com.au/australian-culture/australian-culture-etiquette",
      reliabilityScore: 94,
      confidenceLevel: "Đáng tin cậy (94%)",
      publishedDate: "2023-12-05",
      verifiedDate: "2024-02-12",
      status: "APPROVED"
    }
  ],

  // Dữ liệu câu hỏi mẫu có thể click ngay để thử nghiệm RAG Chatbot
  sampleQueries: [
    {
      text: "Khi làm thêm ở quán ăn Nhật Bản, nếu vô tình làm vỡ bát đĩa thì cách ứng xử đúng chuẩn là gì?",
      country: "JP",
      domain: "cong_viec",
      tags: ["Baito", "Làm thêm", "Horenso"]
    },
    {
      text: "Làm sao để đăng ký địa chỉ thường trú và làm thẻ My Number khi mới tới Tokyo?",
      country: "JP",
      domain: "phap_ly",
      tags: ["Thủ tục", "Kuyakusho", "Visa"]
    },
    {
      text: "Cách cúi chào, xưng hô và đưa nhận đồ với tiền bối (Sunbae) ở trường đại học Hàn Quốc?",
      country: "KR",
      domain: "giao_tiep",
      tags: ["Kính ngữ", "Sunbae", "Văn hóa"]
    },
    {
      text: "Du học sinh Hàn Quốc có bắt buộc phải đóng Bảo hiểm Y tế Quốc dân (NHIS) không và phí bao nhiêu?",
      country: "KR",
      domain: "y_te",
      tags: ["Bảo hiểm", "NHIS", "Y tế"]
    },
    {
      text: "Du học sinh Úc được làm thêm bao nhiêu tiếng mỗi tuần và mức lương tối thiểu Fair Work là bao nhiêu?",
      country: "AU",
      domain: "cong_viec",
      tags: ["Visa 500", "Fair Work", "Lương tối thiểu"]
    },
    {
      text: "Ở nhà hàng tại Sydney hoặc Melbourne có bắt buộc phải tip tiền cho nhân viên không?",
      country: "AU",
      domain: "doi_song",
      tags: ["Tipping", "Tiền tip", "Ăn uống"]
    }
  ],

  // Dữ liệu thống kê chuẩn xác trích xuất từ Trang 22, 23, 24 của Thuyết minh dự án
  dashboardMetrics: {
    // Trang 22: Preparation & Adaptation
    preparation: {
      lowReadiness: 37.7,
      noPreparation: 21.7,
      experiencedUsers: 150,
      highDifficulty: 82.7,
      readinessByStage: [
        { stage: "Chỉ từng đến ngắn hạn như du lịch/công tác", high: 41.33, neutral: 40.00, low: 18.67 },
        { stage: "Đã từng sinh sống/học tập/làm việc tại đó và hiện đã trở về VN", high: 50.67, neutral: 33.33, low: 16.00 },
        { stage: "Đang chuẩn bị đi và chưa từng sinh sống tại đó", high: 44.00, neutral: 36.00, low: 20.00 },
        { stage: "Hiện đang sinh sống/học tập/làm việc tại đó", high: 45.33, neutral: 41.33, low: 13.34 }
      ],
      preparationGaps: [
        { item: "Y tế, bảo hiểm và tình huống khẩn cấp", gap: 89.67 },
        { item: "Thời tiết, mùa và trang phục phù hợp", gap: 89.33 },
        { item: "Visa, cư trú và thủ tục hành chính", gap: 89.33 },
        { item: "Văn hóa học tập hoặc văn hóa nơi làm việc", gap: 88.33 },
        { item: "Nhà ở và hợp đồng thuê nhà", gap: 88.00 }
      ],
      difficultyByCountryTable: [
        { topic: "Cuộc sống hằng ngày", au: 2.38, jp: 2.33, kr: 2.68 },
        { topic: "Giao tiếp", au: 2.60, jp: 2.65, kr: 2.98 },
        { topic: "Học tập/công việc", au: 2.78, jp: 2.38, kr: 2.75 },
        { topic: "Tham gia cộng đồng", au: 3.00, jp: 3.48, kr: 3.16 }
      ],
      difficultyByTopic: [
        { topic: "Tham gia cộng đồng", pct: 42.9 },
        { topic: "Thủ tục hành chính", pct: 37.6 },
        { topic: "Giao tiếp", pct: 36.1 },
        { topic: "Học tập/công việc", pct: 34.9 },
        { topic: "Cuộc sống hằng ngày", pct: 25.7 }
      ],
      adaptationBarriers: [
        { barrier: "Giao tiếp trong quan hệ có sự cách biệt về tuổi tác/thứ bậc", score: 0.22 },
        { barrier: "Hối lại, nhờ giúp đỡ hoặc xin phép cấp trên", score: 0.22 },
        { barrier: "Nghe hoặc nói bằng ngôn ngữ bản địa", score: 0.20 },
        { barrier: "Tốc độ nói, giọng địa phương khó bắt kịp", score: 0.20 },
        { barrier: "Cảm thấy bị xa lánh, định kiến hoặc lạc lõng", score: 0.19 },
        { barrier: "Kết bạn hoặc duy trì quan hệ xã hội", score: 0.19 }
      ]
    },

    // Trang 23: Information Needs & Barriers + Overview
    infoNeeds: {
      infoGaps: 80.3,
      searchDifficulties: 77.3,
      officialReach: 53.7,
      socialUse: 52.0,
      topNeeds: [
        { item: "Ngân hàng, thanh toán và chuyển tiền", pct: 15.3 },
        { item: "Nhà ở và hợp đồng thuê nhà", pct: 14.3 },
        { item: "Cộng đồng, kết bạn và mạng lưới hỗ trợ", pct: 13.7 },
        { item: "Phong tục, ngày lễ và điều nên tránh", pct: 13.7 },
        { item: "Giao thông và di chuyển", pct: 13.3 }
      ],
      sourcesUsed: [
        { source: "Chatbot hoặc công cụ AI", pct: 25.3 },
        { source: "Hội sinh viên, hội người Việt hải ngoại", pct: 23.7 },
        { source: "Nhóm Facebook, Zalo hoặc cộng đồng mạng", pct: 23.3 },
        { source: "Công ty tư vấn du học, tuyển dụng", pct: 23.0 },
        { source: "Trường học, cơ sở đào tạo hoặc nơi làm", pct: 22.7 }
      ],
      informationBarriers: [
        { barrier: "Không biết thông tin có phù hợp hoàn cảnh cụ thể", pct: 21.0 },
        { barrier: "Nội dung mang tính quảng cáo hoặc thiếu khách quan", pct: 20.7 },
        { barrier: "Thông tin nằm rải rác ở quá nhiều nguồn", pct: 20.7 },
        { barrier: "Thông tin quá chung chung, không gắn tình huống", pct: 20.7 },
        { barrier: "Có quy định nhưng không biết nên ứng xử ra sao", pct: 20.3 },
        { barrier: "Khó xác định nguồn nào đáng tin cậy", pct: 20.3 }
      ],
      publishedBenchmarks: [
        { country: "Japan (JASSO 2023)", stat: "46.7%", label: "Former students as an information source" },
        { country: "Australia (QILT 2024)", stat: "92.9%", label: "Positive overall living experience" },
        { country: "South Korea (Published Study)", stat: "22.0%", label: "Reported financial & adaptation difficulties" }
      ],
      surveySample: {
        total: 300,
        highReadiness: 45.3,
        highWillingness: 41.7,
        distribution: [
          { country: "Nhật Bản", share: 33.3 },
          { country: "Hàn Quốc", share: 33.3 },
          { country: "Australia", share: 33.4 }
        ]
      }
    },

    // Trang 24: Human-Centered Product Priorities
    priorities: {
      highUseIntention: 41.7,
      meanUseIntention: 3.03,
      topPreferredFormatPct: 31.7,
      topRequestedSupportPct: 24.0,
      requestedSupport: [
        { item: "Giải thích những tình huống dễ gây hiểu lầm", pct: 24.0 },
        { item: "Checklist chuẩn bị trước khi đi", pct: 23.7 },
        { item: "Cách ứng xử rủi ro trong từng tình huống", pct: 22.3 },
        { item: "Địa chỉ/đường dây hỗ trợ chính thức và cộng đồng", pct: 22.3 },
        { item: "Thông báo khi thông tin quan trọng thay đổi", pct: 22.3 },
        { item: "Ưu tiên nội dung theo mục đích du học/lao động", pct: 21.7 },
        { item: "Danh sách điều nên làm / không nên làm", pct: 21.3 },
        { item: "Hướng dẫn thủ tục kèm nguồn minh bạch", pct: 21.3 },
        { item: "So sánh ngắn gọn giữa Việt Nam và nước sở tại", pct: 21.1 }
      ],
      preferredFormats: [
        { format: "Thông báo/nhắc việc theo thời gian thực", pct: 31.7 },
        { format: "Infographic hoặc video ngắn, trực quan", pct: 31.3 },
        { format: "Thẻ thông tin ngắn, dễ đọc (Evidence Card)", pct: 28.7 },
        { format: "Bảng so sánh Việt Nam - quốc gia đến", pct: 29.3 },
        { format: "Liên kết trực tiếp đến nguồn chính thống", pct: 27.7 },
        { format: "Tình huống mô phỏng với nhiều lựa chọn", pct: 25.0 },
        { format: "Chatbot tương tác hỏi đáp theo ngữ cảnh", pct: 24.7 }
      ],
      useIntentionByStage: [
        { stage: "Chỉ từng đến ngắn hạn", high: 45.33, low: 22.67, neutral: 32.0 },
        { stage: "Đã từng sinh sống/học tập", high: 34.67, low: 24.0, neutral: 41.33 },
        { stage: "Đang chuẩn bị đi", high: 49.33, low: 20.0, neutral: 30.67 },
        { stage: "Hiện đang sinh sống", high: 37.33, low: 25.33, neutral: 37.34 }
      ]
    }
  },

  // Hàng đợi duyệt dành cho Quản trị viên (Admin Approval Queue) - Image 2 & 3
  adminQueue: [
    {
      id: "REV-2026-001",
      type: "SURVEY_SUBMISSION",
      submitter: "Nguyen Van A (Ẩn danh PII)",
      country: "JP",
      countryName: "Nhật Bản",
      domainId: "cong_viec",
      domainName: "Học tập – Công việc",
      submittedAt: "2026-03-28 14:20",
      title: "Trải nghiệm xin nghỉ ốm tại công ty Nhật Bản (Xưng hô & Giấy khám bệnh)",
      experienceText: "Khi bị ốm phải gọi điện báo cho quản lý trước 15 phút giờ vào ca. Không nhắn tin Zalo hay Line vì bị coi là thiếu tôn trọng. Nhớ đi khám tại Clinic địa phương xin Shindan-sho (giấy khám bệnh).",
      sourceCredibility: "Kinh nghiệm thực tế cá nhân (3 năm tại Osaka)",
      status: "PENDING",
      proposedCard: {
        title: "Quy chuẩn xin nghỉ ốm và thông báo cho cấp trên tại Nhật Bản",
        safeAction: "Gọi điện thoại trực tiếp trước giờ làm, nói rõ tình trạng sức khỏe và cam kết đi khám bác sĩ.",
        donots: "Chỉ nhắn tin văn bản rồi tự ý nghỉ khi chưa nhận được phản hồi chấp thuận từ cấp trên."
      }
    },
    {
      id: "REV-2026-002",
      type: "TICKET_FEEDBACK",
      submitter: "Du học sinh Seoul (Ẩn danh)",
      country: "KR",
      countryName: "Hàn Quốc",
      domainId: "y_te",
      domainName: "Y tế – Bảo hiểm",
      submittedAt: "2026-03-29 09:15",
      title: "Cập nhật mức phí đóng bảo hiểm y tế NHIS năm 2026",
      experienceText: "Mức phí bảo hiểm y tế sinh viên quốc tế diện visa D-2 vừa được điều chỉnh tăng nhẹ từ kỳ 2026. Đề nghị hệ thống cập nhật số liệu chính xác để tránh nhầm lẫn.",
      sourceCredibility: "Thông báo chính thức từ Đại học Quốc gia Seoul (SNU)",
      status: "PENDING"
    },
    {
      id: "REV-2026-003",
      type: "OFFICIAL_SOURCE_INGEST",
      submitter: "Hệ thống tự động (dbt/Pandas Pipeline)",
      country: "AU",
      countryName: "Australia",
      domainId: "phap_ly",
      domainName: "Hành chính – Pháp lý",
      submittedAt: "2026-03-30 08:00",
      title: "Cập nhật điều chỉnh visa làm thêm du học sinh 48h/2 tuần từ Home Affairs Úc",
      experienceText: "Bộ Nội vụ Úc gia hạn việc kiểm soát nghiêm ngặt 48h/fortnight. Thêm cảnh báo tự động về trường hợp vi phạm có thể bị hủy visa theo Điều 8105.",
      sourceCredibility: "https://immi.homeaffairs.gov.au",
      status: "APPROVED"
    }
  ]
};
