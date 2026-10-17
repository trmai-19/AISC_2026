/**
 * POWER BI VISUALIZATION MODULE (DCI - AISC 2026)
 * Tái hiện 100% chuẩn xác hệ thống báo cáo Power BI với ĐẦY ĐỦ CÁC LOẠI BIỂU ĐỒ:
 * 1. Vertical Column Chart (Biểu đồ cột đứng: Thang Likert 1-5, Phân bổ ngày hoạt động)
 * 2. SVG Donut Chart (Biểu đồ vành khuyên: Cơ cấu mục đích, Tỷ lệ sẵn sàng cao, Tỷ lệ chuẩn bị thấp)
 * 3. SVG Area Trend Chart (Biểu đồ miền diện tích gradient: Lưu lượng tin nhắn RAG theo tháng)
 * 4. 100% Stacked Bar Chart (Biểu đồ thanh 100%: Giai đoạn thích nghi, Mức chuẩn bị vs sẵn sàng)
 * 5. Clustered Horizontal Bar Chart (Biểu đồ thanh ngang so sánh)
 * 6. Pivot Matrix Table (Bảng ma trận thách thức theo quốc gia)
 * 7. TableEx (Bảng chi tiết kinh nghiệm cộng đồng đã kiểm duyệt)
 * 
 * 5 TRANG BÁO CÁO GỘP THỐNG NHẤT:
 * - Trang 01 (MẶC ĐỊNH MỞ ĐẦU): Sinh viên biết đến hỗ trợ đến đâu (01 / 05)
 * - Trang 02: Trải nghiệm tại điểm đến (Đức, Úc, Nhật Bản) (02 / 05)
 * - Trang 03: Tổng quan cộng đồng (Community Overview) (03 / 05)
 * - Trang 04: Nhu cầu người dùng (User Needs) (04 / 05)
 * - Trang 05: Sử dụng hệ thống (Product Usage) (05 / 05)
 */

let pbiCurrentPage = 1; // MẶC ĐỊNH TRANG 01 MỞ ĐẦU!

let pbiSelectedCountry = 'DE';     // Quốc gia Trang 01
let pbiSelectedDestination = 'DE'; // Điểm đến Trang 02: 'DE' | 'AU' | 'JP'

/**
 * Làm sạch tên quốc gia: loại bỏ phần mã trong ngoặc đơn
 */
function cleanCountryName(str) {
  if (!str) return '';
  return String(str)
    .replace(/\s*\([A-Za-z0-9]+\)/g, '')
    .trim();
}

/**
 * Hàm lọc văn bản:
 * Loại bỏ triệt để các chữ jasso, daad, qilt, bintho, sesaba, cohort,
 * chuẩn hóa "Toàn nhóm quốc tế tại Úc" thành "Nhóm quốc tế tại Úc",
 * loại bỏ các mã trong ngoặc và toàn bộ emoji/icon.
 */
function sanitizePbiText(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/Toàn nhóm quốc tế tại Úc/gi, 'Nhóm quốc tế tại Úc')
    .replace(/Toàn nhóm quốc tế/gi, 'Nhóm quốc tế tại Úc')
    .replace(/\b(JASSO|DAAD|QILT|jasoo|daad|qult)\b/gi, '')
    .replace(/\s*\([A-Za-z0-9]+\)/g, '')
    .replace(/BintHo[^\n;]*/gi, '')
    .replace(/SeSaBa[^\n;]*/gi, '')
    .replace(/cohort[^\n;]*/gi, '')
    .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F1E6}-\u{1F1FF}]/gu, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getSafeField(obj, fieldName) {
  if (!obj) return undefined;
  if (obj[fieldName] !== undefined) return obj[fieldName];
  if (obj['\ufeff' + fieldName] !== undefined) return obj['\ufeff' + fieldName];
  return undefined;
}

function initDashboard() {
  const container = document.getElementById('dashboard-container');
  if (!container) return;

  if (typeof AISC_DASHBOARD_DATA === 'undefined') {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px dashed var(--border-subtle);">
        <p style="color: var(--text-muted); font-size: 0.95rem;">Đang tải bộ dữ liệu thống kê...</p>
      </div>
    `;
    return;
  }

  if (!AISC_DASHBOARD_DATA.destinationChartData && AISC_DASHBOARD_DATA.destinationCharts) {
    AISC_DASHBOARD_DATA.destinationChartData = AISC_DASHBOARD_DATA.destinationCharts;
  }

  renderPowerBIDashboard();
}

/**
 * Chuyển đổi giữa 5 trang thống nhất
 */
function switchPbiPage(pageIndex) {
  pbiCurrentPage = Number(pageIndex);
  renderPowerBIDashboard();
}

// Các hàm tương thích ngược
function switchPbiReport(rep) {
  pbiCurrentPage = (rep === 'aisc') ? 3 : 1;
  renderPowerBIDashboard();
}

function switchPbiNgoaiPage(page) {
  pbiCurrentPage = (page === 'destination') ? 2 : 1;
  renderPowerBIDashboard();
}

function switchPbiAiscPage(page) {
  if (page === 'needs') pbiCurrentPage = 4;
  else if (page === 'product') pbiCurrentPage = 5;
  else pbiCurrentPage = 3;
  renderPowerBIDashboard();
}

function selectPbiDestination(destCode) {
  pbiSelectedDestination = destCode;
  renderPowerBIDashboard();
}

function selectPbiCountry(countryCode) {
  pbiSelectedCountry = countryCode;
  renderPowerBIDashboard();
}

function getPageMetadata(pageIndex) {
  switch (pageIndex) {
    case 1:
      return {
        eyebrow: 'DCI  /  BẰNG CHỨNG THỰC TẾ',
        title: 'Sinh viên biết đến hỗ trợ đến đâu'
      };
    case 2:
      return {
        eyebrow: 'DCI  /  BẰNG CHỨNG THỰC TẾ',
        title: 'Trải nghiệm tại điểm đến'
      };
    case 3:
      return {
        eyebrow: 'DCI  /  HỆ THỐNG VÀ CỘNG ĐỒNG',
        title: 'Tổng quan cộng đồng'
      };
    case 4:
      return {
        eyebrow: 'DCI  /  HỆ THỐNG VÀ CỘNG ĐỒNG',
        title: 'Nhu cầu & Thách thức'
      };
    case 5:
      return {
        eyebrow: 'DCI  /  HỆ THỐNG VÀ CỘNG ĐỒNG',
        title: 'Tình hình sử dụng sản phẩm'
      };
    default:
      return {
        eyebrow: 'DCI  /  BÁO CÁO THỐNG KÊ',
        title: 'Báo cáo số liệu'
      };
  }
}

/**
 * RENDER CHÍNH: KHUNG BÁO CÁO GỘP THỐNG NHẤT
 */
function renderPowerBIDashboard() {
  const container = document.getElementById('dashboard-container');
  if (!container) return;

  const meta = getPageMetadata(pbiCurrentPage);

  container.innerHTML = `
    <div class="pbi-report-wrapper">
      <!-- Top Header Bar -->
      <div class="pbi-topbar">
        <div class="pbi-title-group">
          <div class="pbi-eyebrow">${escapeHtml(meta.eyebrow)}</div>
          <h1 class="pbi-report-title">${escapeHtml(meta.title)}</h1>
        </div>

        <div class="pbi-controls-cluster">
          <!-- Slicer lọc theo từng trang -->
          <div class="pbi-slicer-wrap">
            ${pbiCurrentPage === 1 ? renderOverviewSlicer() : ''}
            ${pbiCurrentPage === 2 ? renderDestinationSlicer() : ''}
          </div>
        </div>
      </div>

      <!-- Thanh điều hướng 5 trang chuẩn Power BI gộp thống nhất -->
      <div class="pbi-unified-nav">
        <button class="pbi-unified-nav-tab ${pbiCurrentPage === 1 ? 'active' : ''}" onclick="switchPbiPage(1)">
          1. Biết đến hỗ trợ
        </button>
        <button class="pbi-unified-nav-tab ${pbiCurrentPage === 2 ? 'active' : ''}" onclick="switchPbiPage(2)">
          2. Trải nghiệm điểm đến
        </button>
        <button class="pbi-unified-nav-tab ${pbiCurrentPage === 3 ? 'active' : ''}" onclick="switchPbiPage(3)">
          3. Tổng quan cộng đồng
        </button>
        <button class="pbi-unified-nav-tab ${pbiCurrentPage === 4 ? 'active' : ''}" onclick="switchPbiPage(4)">
          4. Nhu cầu người dùng
        </button>
        <button class="pbi-unified-nav-tab ${pbiCurrentPage === 5 ? 'active' : ''}" onclick="switchPbiPage(5)">
          5. Sử dụng hệ thống
        </button>
      </div>

      <!-- Nội dung trang báo cáo đang được chọn -->
      ${renderActivePageContent(pbiCurrentPage)}
    </div>
  `;
}

function renderActivePageContent(pageIndex) {
  switch (pageIndex) {
    case 1:
      return renderOverviewPage();
    case 2:
      return renderDestinationPage();
    case 3:
      return renderAiscOverviewPage();
    case 4:
      return renderAiscNeedsPage();
    case 5:
      return renderAiscProductPage();
    default:
      return renderOverviewPage();
  }
}

/**
 * ===================================================================
 * COMPONENT: MINI DONUT FOR KPI CARDS
 * ===================================================================
 */
function renderSvgMiniDonut(pct, color = 'var(--accent-primary)') {
  const r = 20;
  const c = 2 * Math.PI * r; // ~125.66
  const filled = (Math.min(pct, 100) / 100) * c;
  const empty = c - filled;
  return `
    <svg viewBox="0 0 52 52" class="pbi-card-donut-svg">
      <circle cx="26" cy="26" r="${r}" fill="none" stroke="var(--bg-primary)" stroke-width="6"/>
      <circle cx="26" cy="26" r="${r}" fill="none" stroke="${color}" stroke-width="6"
        stroke-dasharray="${filled.toFixed(2)} ${empty.toFixed(2)}" stroke-dashoffset="0" stroke-linecap="round"/>
    </svg>
  `;
}

/**
 * ===================================================================
 * COMPONENT: FULL SVG DONUT CHART (donutChart in Power BI)
 * ===================================================================
 */
function renderSvgDonutChart(slices, totalLabel, totalVal) {
  const r = 85;
  const c = 2 * Math.PI * r; // ~534.07
  let accumulatedOffset = 0;

  const circlesHtml = slices.map(s => {
    const sliceLen = (s.pct / 100) * c;
    const remaining = c - sliceLen;
    const offset = -accumulatedOffset;
    accumulatedOffset += sliceLen;

    return `
      <circle cx="120" cy="120" r="${r}" fill="none" stroke="${s.color}" stroke-width="26"
        stroke-dasharray="${sliceLen.toFixed(2)} ${remaining.toFixed(2)}"
        stroke-dashoffset="${offset.toFixed(2)}"
        style="transition: all 0.3s ease;">
        <title>${escapeHtml(s.label)}: ${s.count} (${s.pct}%)</title>
      </circle>
    `;
  }).join('');

  const legendHtml = slices.map(s => `
    <div class="pbi-donut-legend-item">
      <div class="pbi-donut-legend-left">
        <span class="pbi-donut-legend-dot" style="background: ${s.color};"></span>
        <span style="font-weight: 600;">${escapeHtml(s.label)}</span>
      </div>
      <div class="pbi-donut-legend-right">${s.count} (${s.pct}%)</div>
    </div>
  `).join('');

  return `
    <div class="pbi-donut-container">
      <div class="pbi-donut-wrap">
        <svg viewBox="0 0 240 240" class="pbi-donut-svg">
          <circle cx="120" cy="120" r="${r}" fill="none" stroke="var(--bg-primary)" stroke-width="26"/>
          ${circlesHtml}
        </svg>
        <div class="pbi-donut-center">
          <div class="pbi-donut-center-val">${escapeHtml(totalVal)}</div>
          <div class="pbi-donut-center-lbl">${escapeHtml(totalLabel)}</div>
        </div>
      </div>
      <div class="pbi-donut-legend">
        ${legendHtml}
      </div>
    </div>
  `;
}

/**
 * ===================================================================
 * COMPONENT: VERTICAL COLUMN CHART (columnChart / clusteredColumnChart)
 * ===================================================================
 */
function renderVerticalColumnChart(items, valKey, labelKey, maxVal, colorMode = 'emerald') {
  const safeMax = maxVal || Math.max(...items.map(d => Number(d[valKey] || 0)), 1);

  const colsHtml = items.map(item => {
    const val = Number(item[valKey] || 0);
    const heightPct = Math.min((val / safeMax) * 100, 100);
    const label = sanitizePbiText(item[labelKey] || '');
    const displayVal = item.displayVal || val;

    return `
      <div class="pbi-vcol-col-item">
        <div class="pbi-vcol-val">${escapeHtml(String(displayVal))}</div>
        <div class="pbi-vcol-bar ${colorMode === 'ocean' ? 'ocean' : ''}" style="height: ${heightPct.toFixed(1)}%;"></div>
      </div>
    `;
  }).join('');

  const labelsHtml = items.map(item => `
    <div class="pbi-vcol-label" title="${escapeHtml(item[labelKey])}">
      ${escapeHtml(sanitizePbiText(item[labelKey]))}
    </div>
  `).join('');

  return `
    <div class="pbi-vcol-chart">
      <div class="pbi-vcol-gridlines">
        <div class="pbi-vcol-gridline"></div>
        <div class="pbi-vcol-gridline"></div>
        <div class="pbi-vcol-gridline"></div>
        <div class="pbi-vcol-gridline"></div>
      </div>
      <div class="pbi-vcol-columns-wrap">
        ${colsHtml}
      </div>
      <div class="pbi-vcol-labels-wrap">
        ${labelsHtml}
      </div>
    </div>
  `;
}

/**
 * ===================================================================
 * COMPONENT: SVG AREA TREND CHART (areaChart in Power BI)
 * ===================================================================
 */
function renderSvgAreaTrendChart(points) {
  if (!points || points.length === 0) return '';

  const maxVal = Math.max(...points.map(p => p.messages), 1) * 1.15;
  const width = 500;
  const height = 180;
  const padX = 40;
  const padY = 25;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const coords = points.map((p, idx) => {
    const x = padX + (idx / (points.length - 1)) * chartW;
    const y = height - padY - (p.messages / maxVal) * chartH;
    return { x, y, ...p };
  });

  const lineD = coords.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, '');

  const areaD = `${lineD} L ${coords[coords.length - 1].x} ${height - padY} L ${coords[0].x} ${height - padY} Z`;

  const circlesHtml = coords.map(pt => `
    <g>
      <circle cx="${pt.x}" cy="${pt.y}" r="5" fill="var(--accent-primary)" stroke="var(--bg-surface)" stroke-width="2"/>
      <text x="${pt.x}" y="${pt.y - 10}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--text-primary)">
        ${pt.messages}
      </text>
    </g>
  `).join('');

  const axisLabelsHtml = points.map(p => `
    <span>${escapeHtml(p.month)}</span>
  `).join('');

  return `
    <div class="pbi-area-chart-container">
      <svg viewBox="0 0 ${width} ${height}" class="pbi-area-svg">
        <defs>
          <linearGradient id="areaGradientEmerald" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--accent-primary)" stop-opacity="0.45"/>
            <stop offset="100%" stop-color="var(--accent-primary)" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        <!-- Horizontal Gridlines -->
        <line x1="${padX}" y1="${padY}" x2="${width - padX}" y2="${padY}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 3"/>
        <line x1="${padX}" y1="${height/2}" x2="${width - padX}" y2="${height/2}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 3"/>
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="rgba(255,255,255,0.15)"/>
        <!-- Filled Area -->
        <path d="${areaD}" fill="url(#areaGradientEmerald)"/>
        <!-- Line Stroke -->
        <path d="${lineD}" fill="none" stroke="var(--accent-primary)" stroke-width="3" stroke-linecap="round"/>
        <!-- Data points -->
        ${circlesHtml}
      </svg>
      <div class="pbi-area-axis-labels">
        ${axisLabelsHtml}
      </div>
    </div>
  `;
}

/**
 * ===================================================================
 * COMPONENT: 100% STACKED BAR CHART (hundredPercentStackedBarChart)
 * ===================================================================
 */
function render100PercentStackedBarChart(rows) {
  const legendHtml = `
    <div class="pbi-chart-legend" style="margin-bottom: 0.75rem;">
      <div class="pbi-legend-item">
        <span class="pbi-legend-color" style="background: var(--accent-ocean);"></span>
        <span>Nguy cơ chuẩn bị thấp</span>
      </div>
      <div class="pbi-legend-item">
        <span class="pbi-legend-color" style="background: var(--accent-primary);"></span>
        <span>Đã chuẩn bị tốt</span>
      </div>
    </div>
  `;

  const rowsHtml = rows.map(r => {
    const low = Number(r.low_prep_pct || 0);
    const good = Number((100 - low).toFixed(1));

    return `
      <div class="pbi-stacked-row">
        <div class="pbi-stacked-header">
          <span>${escapeHtml(r.stage || r.label)}</span>
          <span style="color: var(--text-muted); font-size: 0.75rem;">n = ${r.count || 75}</span>
        </div>
        <div class="pbi-stacked-bar-track">
          <div class="pbi-stacked-segment" style="width: ${low}%; background: var(--accent-ocean);" title="Chuẩn bị thấp: ${low}%">
            ${low > 15 ? low + '%' : ''}
          </div>
          <div class="pbi-stacked-segment" style="width: ${good}%; background: var(--accent-primary);" title="Chuẩn bị tốt: ${good}%">
            ${good > 15 ? good + '%' : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    ${legendHtml}
    <div class="pbi-stacked-container">
      ${rowsHtml}
    </div>
  `;
}

/**
 * ===================================================================
 * BỘ LỌC SLICER (QUỐC GIA & ĐIỂM ĐẾN)
 * ===================================================================
 */
function renderOverviewSlicer() {
  const countries = AISC_DASHBOARD_DATA.overviewCountries || [];
  
  let optionsHtml = '';
  countries.forEach(c => {
    const code = getSafeField(c, 'country_code');
    const rawName = c.country_name || code;
    const cleanName = cleanCountryName(rawName);
    const selected = code === pbiSelectedCountry ? 'selected' : '';
    optionsHtml += `<option value="${escapeHtml(code)}" ${selected}>${escapeHtml(cleanName)}</option>`;
  });

  return `
    <span class="pbi-slicer-label">Quốc gia đang xem:</span>
    <select class="pbi-select-slicer" id="pbiCountrySelect" onchange="selectPbiCountry(this.value)">
      ${optionsHtml}
    </select>
  `;
}

function renderDestinationSlicer() {
  const configs = AISC_DASHBOARD_DATA.destinationConfig || [
    { host_country_code: 'DE', destination_label: 'Đức' },
    { host_country_code: 'AU', destination_label: 'Úc' },
    { host_country_code: 'JP', destination_label: 'Nhật Bản' }
  ];
  
  return `
    <span class="pbi-slicer-label">Điểm đến đang xem:</span>
    <div class="pbi-slicer-pills">
      ${configs.map(cfg => {
        const code = getSafeField(cfg, 'host_country_code');
        const rawLabel = cfg.destination_label || code;
        const cleanLabel = cleanCountryName(rawLabel);
        const isActive = code === pbiSelectedDestination;
        return `
          <button class="pbi-slicer-btn ${isActive ? 'active' : ''}" onclick="selectPbiDestination('${escapeHtml(code)}')">
            ${escapeHtml(cleanLabel)}
          </button>
        `;
      }).join('')}
    </div>
  `;
}

/**
 * ===================================================================
 * TRANG 01: SINH VIÊN BIẾT ĐẾN HỖ TRỢ ĐẾN ĐÂU (01 / 05)
 * ===================================================================
 */
function renderOverviewPage() {
  const cards = (AISC_DASHBOARD_DATA.overviewCards || []).filter(c => getSafeField(c, 'country_code') === pbiSelectedCountry);
  const benchmarks = (AISC_DASHBOARD_DATA.overviewBenchmarks || []).filter(b => getSafeField(b, 'country_code') === pbiSelectedCountry);
  const services = (AISC_DASHBOARD_DATA.overviewServices || []).filter(s => getSafeField(s, 'country_code') === pbiSelectedCountry);

  const sortedCards = [...cards].sort((a, b) => Number(a.slot || 0) - Number(b.slot || 0));

  return `
    <div class="pbi-cards-grid">
      ${[1, 2, 3, 4].map(slotNum => {
        const card = sortedCards.find(c => Number(c.slot) === slotNum);
        let displayVal = '—';
        let label = 'Chưa nghe đến tư vấn';
        if (card) {
          label = sanitizePbiText(card.card_label);
          if (card.value_pct && card.value_pct !== '' && !isNaN(Number(card.value_pct))) {
            displayVal = Number(card.value_pct).toFixed(1) + '%';
          } else {
            displayVal = 'Chưa có số liệu';
          }
        }
        return `
          <div class="pbi-card-visual">
            <div class="pbi-card-callout">${escapeHtml(displayVal)}</div>
            <div class="pbi-card-label">${escapeHtml(label)}</div>
          </div>
        `;
      }).join('')}
    </div>

    <div class="pbi-charts-grid">
      <!-- Biểu đồ trái: Phân rã 3 trạng thái của dịch vụ -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Tỷ lệ sinh viên theo trạng thái biết đến dịch vụ</div>
        </div>
        
        <div class="pbi-chart-legend">
          <div class="pbi-legend-item">
            <span class="pbi-legend-color" style="background: var(--accent-primary);"></span>
            <span>Đã sử dụng</span>
          </div>
          <div class="pbi-legend-item">
            <span class="pbi-legend-color" style="background: var(--accent-ocean);"></span>
            <span>Biết nhưng chưa dùng</span>
          </div>
          <div class="pbi-legend-item">
            <span class="pbi-legend-color" style="background: var(--text-muted);"></span>
            <span>Chưa nghe đến</span>
          </div>
        </div>

        <div class="pbi-bars-container">
          ${renderOverviewServicesBars(services)}
        </div>
      </div>

      <!-- Biểu đồ phải: So sánh với trung vị các quốc gia -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">So sánh với trung vị các quốc gia</div>
        </div>

        <div class="pbi-chart-legend">
          <div class="pbi-legend-item">
            <span class="pbi-legend-color" style="background: var(--accent-primary);"></span>
            <span>Quốc gia đang chọn</span>
          </div>
          <div class="pbi-legend-item">
            <span class="pbi-legend-color" style="background: var(--accent-ocean);"></span>
            <span>Trung vị các quốc gia</span>
          </div>
        </div>

        <div class="pbi-bars-container">
          ${renderOverviewBenchmarksBars(benchmarks)}
        </div>
      </div>
    </div>
  </div>
  `;
}

function renderOverviewServicesBars(services) {
  const grouped = {};
  services.forEach(s => {
    const sLabel = sanitizePbiText(s.service_label);
    if (!grouped[sLabel]) grouped[sLabel] = {};
    const state = sanitizePbiText(s.state_label);
    grouped[sLabel][state] = s.value_pct && !isNaN(Number(s.value_pct)) ? Number(s.value_pct) : 0;
  });

  const keys = Object.keys(grouped);
  if (keys.length === 0) {
    return `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.85rem;">Quốc gia này chưa có phân rã dữ liệu dịch vụ chi tiết.</div>`;
  }

  return keys.map(serviceName => {
    const data = grouped[serviceName];
    const valUsed = data['Đã sử dụng'] || 0;
    const valKnown = data['Biết nhưng chưa dùng'] || 0;
    const valUnheard = data['Chưa nghe đến'] || 0;

    return `
      <div class="pbi-bar-row">
        <div class="pbi-bar-label" title="${escapeHtml(serviceName)}">${escapeHtml(serviceName)}</div>
        <div class="pbi-bar-track-wrap">
          <div class="pbi-bar-track" style="display: flex;">
            <div class="pbi-bar-fill" style="width: ${Math.min(valUsed, 100)}%; background: var(--accent-primary);" title="Đã sử dụng: ${valUsed.toFixed(1)}%"></div>
            <div class="pbi-bar-fill" style="width: ${Math.min(valKnown, 100)}%; background: var(--accent-ocean);" title="Biết nhưng chưa dùng: ${valKnown.toFixed(1)}%"></div>
            <div class="pbi-bar-fill" style="width: ${Math.min(valUnheard, 100)}%; background: rgba(148, 163, 184, 0.4);" title="Chưa nghe đến: ${valUnheard.toFixed(1)}%"></div>
          </div>
          <div class="pbi-bar-val">
            ${valUsed > 0 ? valUsed.toFixed(1) + '%' : '—'}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderOverviewBenchmarksBars(benchmarks) {
  if (!benchmarks || benchmarks.length === 0) {
    return `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.85rem;">Chưa có dữ liệu so sánh trung vị.</div>`;
  }

  const sorted = [...benchmarks].sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0));

  return sorted.map(b => {
    const label = sanitizePbiText(b.metric_label);
    const val = b.value_pct && !isNaN(Number(b.value_pct)) ? Number(b.value_pct) : null;
    const med = b.median_pct && !isNaN(Number(b.median_pct)) ? Number(b.median_pct) : 0;

    return `
      <div style="margin-bottom: 0.85rem;">
        <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">
          ${escapeHtml(label)}
        </div>
        <div class="pbi-bar-row" style="margin-bottom: 0.25rem;">
          <div class="pbi-bar-label" style="width: 110px; min-width: 110px; font-size: 0.75rem; color: var(--accent-primary); font-weight: 600;">
            Quốc gia này
          </div>
          <div class="pbi-bar-track-wrap">
            <div class="pbi-bar-track">
              <div class="pbi-bar-fill" style="width: ${val !== null ? Math.min(val, 100) : 0}%; background: var(--accent-primary);"></div>
            </div>
            <div class="pbi-bar-val">${val !== null ? val.toFixed(1) + '%' : '—'}</div>
          </div>
        </div>
        <div class="pbi-bar-row">
          <div class="pbi-bar-label" style="width: 110px; min-width: 110px; font-size: 0.75rem; color: var(--accent-ocean);">
            Trung vị
          </div>
          <div class="pbi-bar-track-wrap">
            <div class="pbi-bar-track">
              <div class="pbi-bar-fill" style="width: ${Math.min(med, 100)}%; background: var(--accent-ocean);"></div>
            </div>
            <div class="pbi-bar-val">${med.toFixed(1)}%</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * ===================================================================
 * TRANG 02: TRẢI NGHIỆM TẠI ĐIỂM ĐẾN (02 / 05)
 * ===================================================================
 */
function renderDestinationPage() {
  const configs = AISC_DASHBOARD_DATA.destinationConfig || [];
  const currConfig = configs.find(c => getSafeField(c, 'host_country_code') === pbiSelectedDestination) || configs[0] || {};

  const cards = (AISC_DASHBOARD_DATA.destinationCards || []).filter(c => getSafeField(c, 'host_country_code') === pbiSelectedDestination);
  const sortedCards = [...cards].sort((a, b) => Number(a.slot || 0) - Number(b.slot || 0));

  const allCharts = AISC_DASHBOARD_DATA.destinationCharts || AISC_DASHBOARD_DATA.destinationChartData || [];
  const chartData = allCharts.filter(d => getSafeField(d, 'host_country_code') === pbiSelectedDestination);
  
  const leftItems = chartData.filter(d => d.panel === 'left');
  const rightItems = chartData.filter(d => d.panel === 'right');

  const leftTitle = sanitizePbiText(currConfig.left_title);
  const rightTitle = sanitizePbiText(currConfig.right_title);

  return `
    <div class="pbi-cards-grid">
      ${[1, 2, 3, 4].map(slotNum => {
        const card = sortedCards.find(c => Number(c.slot) === slotNum);
        let valStr = '—';
        let label = 'Chỉ số trải nghiệm';
        if (card) {
          label = sanitizePbiText(card.card_label);
          if (card.value_pct && !isNaN(Number(card.value_pct))) {
            valStr = Number(card.value_pct).toFixed(1) + '%';
          }
        }
        return `
          <div class="pbi-card-visual">
            <div class="pbi-card-callout">${escapeHtml(valStr)}</div>
            <div class="pbi-card-label">${escapeHtml(label)}</div>
          </div>
        `;
      }).join('')}
    </div>

    <div class="pbi-charts-grid">
      <!-- Biểu đồ trái (Left Clustered Bar Chart) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">${escapeHtml(leftTitle)}</div>
        </div>

        <div class="pbi-bars-container">
          ${renderDestinationLeftBars(leftItems)}
        </div>
      </div>

      <!-- Biểu đồ phải (Right Clustered Bar Chart) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">${escapeHtml(rightTitle)}</div>
        </div>

        ${renderDestinationRightBars(rightItems)}
      </div>
    </div>
  </div>
  `;
}

function renderDestinationLeftBars(items) {
  if (!items || items.length === 0) {
    return `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.85rem;">Không có số liệu.</div>`;
  }

  const sorted = [...items].sort((a, b) => Number(b.value_pct || 0) - Number(a.value_pct || 0));

  return sorted.map(item => {
    const label = sanitizePbiText(item.indicator_label_vi);
    const val = Number(item.value_pct || 0);

    return `
      <div class="pbi-bar-row" title="${escapeHtml(label)}">
        <div class="pbi-bar-label">${escapeHtml(label)}</div>
        <div class="pbi-bar-track-wrap">
          <div class="pbi-bar-track">
            <div class="pbi-bar-fill" style="width: ${Math.min(val, 100)}%; background: var(--accent-primary);"></div>
          </div>
          <div class="pbi-bar-val">${val.toFixed(1)}%</div>
        </div>
      </div>
    `;
  }).join('');
}

function renderDestinationRightBars(items) {
  if (!items || items.length === 0) {
    return `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.85rem;">Không có số liệu.</div>`;
  }

  const groups = [...new Set(items.map(d => sanitizePbiText(d.group_label || 'Tất cả')))];

  const indicatorsMap = {};
  items.forEach(d => {
    const indName = sanitizePbiText(d.indicator_label_vi);
    if (!indicatorsMap[indName]) indicatorsMap[indName] = {};
    const grp = sanitizePbiText(d.group_label || 'Tất cả');
    indicatorsMap[indName][grp] = Number(d.value_pct || 0);
  });

  const legendHtml = `
    <div class="pbi-chart-legend">
      ${groups.map((grp, idx) => `
        <div class="pbi-legend-item">
          <span class="pbi-legend-color" style="background: ${idx === 0 ? 'var(--accent-primary)' : 'var(--accent-ocean)'};"></span>
          <span>${escapeHtml(grp)}</span>
        </div>
      `).join('')}
    </div>
  `;

  const barsHtml = Object.keys(indicatorsMap).map(indName => {
    const dataObj = indicatorsMap[indName];

    return `
      <div style="margin-bottom: 0.85rem;">
        <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem;">
          ${escapeHtml(indName)}
        </div>
        ${groups.map((grp, gIdx) => {
          const val = dataObj[grp] !== undefined ? dataObj[grp] : null;
          const color = gIdx === 0 ? 'var(--accent-primary)' : 'var(--accent-ocean)';
          return `
            <div class="pbi-bar-row" style="margin-bottom: 0.2rem;">
              <div class="pbi-bar-label" style="width: 140px; min-width: 140px; font-size: 0.74rem; color: ${color}; font-weight: 600;">
                ${escapeHtml(grp)}
              </div>
              <div class="pbi-bar-track-wrap">
                <div class="pbi-bar-track">
                  <div class="pbi-bar-fill" style="width: ${val !== null ? Math.min(val, 100) : 0}%; background: ${color};"></div>
                </div>
                <div class="pbi-bar-val">${val !== null ? val.toFixed(1) + '%' : '—'}</div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }).join('');

  return `
    ${legendHtml}
    <div class="pbi-bars-container">
      ${barsHtml}
    </div>
  `;
}

/**
 * ===================================================================
 * TRANG 03: TỔNG QUAN CỘNG ĐỒNG (COMMUNITY OVERVIEW) (03 / 05)
 * CÁC BIỂU ĐỒ ĐA DẠNG:
 * - 2 Donut Mini trong KPI
 * - Vertical Column Chart (Thang Likert 1-5)
 * - 100% Stacked Bar (Giai đoạn thích nghi)
 * - Full SVG Donut Chart (Cơ cấu mục đích xuất cảnh)
 * - Clustered Bar Chart (Số người theo quốc gia)
 * ===================================================================
 */
function renderAiscOverviewPage() {
  const data = (AISC_DASHBOARD_DATA.aiscReportData && AISC_DASHBOARD_DATA.aiscReportData.overview) || {};
  const kpis = data.kpis || { contribution_count: 300, participant_count: 300, high_use_intention_pct: 41.7, low_preparation_pct: 37.7 };
  const intentions = data.useIntention || [];
  const countries = data.countries || [];
  const purposes = data.purposes || [];
  const stages = data.stages || [];

  // Chuẩn bị dữ liệu cho Donut Chart: Cơ cấu mục đích
  const purposeDonutSlices = [
    { label: 'Du học', count: 210, pct: 70.0, color: 'var(--accent-primary)' },
    { label: 'Lao động', count: 60, pct: 20.0, color: 'var(--accent-ocean)' },
    { label: 'Định cư', count: 30, pct: 10.0, color: '#F59E0B' }
  ];

  // Chuẩn bị dữ liệu cho Vertical Column Chart: Likert 1-5
  const likertItems = intentions.map(item => ({
    label: item.score.split(' ')[0], // '1', '2', '3', '4', '5'
    count: item.count,
    displayVal: `${item.count} (${item.pct}%)`
  }));

  return `
    <!-- 4 Cards Row với Donut Indicators -->
    <div class="pbi-cards-grid">
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.contribution_count}</div>
        <div class="pbi-card-label">Contribution</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.participant_count}</div>
        <div class="pbi-card-label">Participant</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-with-donut">
          <div>
            <div class="pbi-card-callout">${kpis.high_use_intention_pct}</div>
            <div class="pbi-card-label">High Use Intention</div>
          </div>
          ${renderSvgMiniDonut(kpis.high_use_intention_pct, 'var(--accent-primary)')}
        </div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-with-donut">
          <div>
            <div class="pbi-card-callout">${kpis.low_preparation_pct}</div>
            <div class="pbi-card-label">Low Preparation</div>
          </div>
          ${renderSvgMiniDonut(kpis.low_preparation_pct, 'var(--accent-ocean)')}
        </div>
      </div>
    </div>

    <!-- HÀNG 1: Vertical Column Chart & 100% Stacked Bar -->
    <div class="pbi-charts-grid">
      <!-- Visual 1: Vertical Column Chart (Thang đo Likert) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Mức độ sẵn sàng sử dụng giải pháp DCI (Thang điểm 1-5)</div>
        </div>
        ${renderVerticalColumnChart(likertItems, 'count', 'label', 120, 'emerald')}
      </div>

      <!-- Visual 2: 100% Stacked Bar Chart (Giai đoạn thích nghi) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Giai đoạn hành trình & Nguy cơ thiếu chuẩn bị (100% Stacked)</div>
        </div>
        ${render100PercentStackedBarChart(stages)}
      </div>
    </div>

    <!-- HÀNG 2: SVG Donut Chart & Clustered Bar -->
    <div class="pbi-charts-grid">
      <!-- Visual 3: SVG Donut Chart (Cơ cấu mục đích xuất cảnh) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Cơ cấu mục đích xuất cảnh (Donut Chart)</div>
        </div>
        ${renderSvgDonutChart(purposeDonutSlices, 'Tổng số', '300 hồ sơ')}
      </div>

      <!-- Visual 4: Clustered Bar Chart (Số người theo quốc gia) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Số người tham gia theo quốc gia</div>
        </div>
        <div class="pbi-bars-container">
          ${countries.map(co => `
            <div class="pbi-bar-row">
              <div class="pbi-bar-label">${escapeHtml(co.country)}</div>
              <div class="pbi-bar-track-wrap">
                <div class="pbi-bar-track">
                  <div class="pbi-bar-fill" style="width: ${co.pct * 2.5}%; background: var(--accent-ocean);"></div>
                </div>
                <div class="pbi-bar-val">${co.count} người</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  </div>
  `;
}

/**
 * ===================================================================
 * TRANG 04: NHU CẦU NGƯỜI DÙNG (USER NEEDS) (04 / 05)
 * CÁC BIỂU ĐỒ ĐA DẠNG:
 * - 100% Stacked Bar Chart
 * - Clustered Bar Chart
 * - Pivot Matrix Table
 * - Detailed Data Table
 * ===================================================================
 */
function renderAiscNeedsPage() {
  const data = (AISC_DASHBOARD_DATA.aiscReportData && AISC_DASHBOARD_DATA.aiscReportData.userNeeds) || {};
  const kpis = data.kpis || { contribution_count: 300, participant_count: 300, high_use_intention_pct: 41.7, low_preparation_pct: 37.7 };
  const challenges = data.challenges || [];
  const matrix = data.challengesByCountry || [];
  const exps = data.experiences || [];

  const prepCorrelationRows = [
    { label: 'Nhóm chuẩn bị thấp (n = 113)', count: 113, low_prep_pct: 68.2 },
    { label: 'Nhóm chuẩn bị tốt (n = 187)', count: 187, low_prep_pct: 25.7 }
  ];

  return `
    <div class="pbi-cards-grid">
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.contribution_count}</div>
        <div class="pbi-card-label">Contribution</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.participant_count}</div>
        <div class="pbi-card-label">Participant</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-with-donut">
          <div>
            <div class="pbi-card-callout">${kpis.high_use_intention_pct}</div>
            <div class="pbi-card-label">High Use Intention</div>
          </div>
          ${renderSvgMiniDonut(kpis.high_use_intention_pct, 'var(--accent-primary)')}
        </div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-with-donut">
          <div>
            <div class="pbi-card-callout">${kpis.low_preparation_pct}</div>
            <div class="pbi-card-label">Low Preparation</div>
          </div>
          ${renderSvgMiniDonut(kpis.low_preparation_pct, 'var(--accent-ocean)')}
        </div>
      </div>
    </div>

    <div class="pbi-charts-grid">
      <!-- Visual 1: 100% Stacked Bar (Mối tương quan chuẩn bị vs nhu cầu) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Mối liên hệ giữa Mức chuẩn bị và Nguy cơ phát sinh rủi ro</div>
        </div>
        ${render100PercentStackedBarChart(prepCorrelationRows)}
      </div>

      <!-- Visual 2: Clustered Bar Chart (Top thách thức thực tế) -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Thách thức và khó khăn thực tế được phản ánh</div>
        </div>
        <div class="pbi-bars-container">
          ${challenges.map(ch => `
            <div class="pbi-bar-row">
              <div class="pbi-bar-label">${escapeHtml(ch.challenge)}</div>
              <div class="pbi-bar-track-wrap">
                <div class="pbi-bar-track">
                  <div class="pbi-bar-fill" style="width: ${ch.pct}%; background: var(--accent-primary);"></div>
                </div>
                <div class="pbi-bar-val">${ch.pct}%</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <!-- HÀNG 2: Pivot Table & Detailed Table -->
    <div class="pbi-charts-grid" style="margin-top: 1rem;">
      <!-- Visual 3: Pivot Table Matrix -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Ma trận thách thức theo quốc gia (%)</div>
        </div>
        <div class="pbi-table-wrap">
          <table class="pbi-table">
            <thead>
              <tr>
                <th>Lĩnh vực thách thức</th>
                <th>Nhật Bản</th>
                <th>Hàn Quốc</th>
                <th>Úc</th>
              </tr>
            </thead>
            <tbody>
              ${matrix.map(m => `
                <tr>
                  <td><strong>${escapeHtml(m.challenge)}</strong></td>
                  <td style="color: var(--accent-primary); font-weight: 600;">${m.JP}%</td>
                  <td style="color: var(--accent-ocean); font-weight: 600;">${m.KR}%</td>
                  <td style="color: var(--text-primary); font-weight: 600;">${m.AU}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Visual 4: TableEx -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Kinh nghiệm thực tế từ cộng đồng (Đã kiểm duyệt & tích hợp)</div>
        </div>
        <div class="pbi-table-wrap">
          <table class="pbi-table">
            <thead>
              <tr>
                <th style="width: 100px;">Quốc gia</th>
                <th style="width: 110px;">Lĩnh vực</th>
                <th>Tiêu đề tình huống thực tế</th>
              </tr>
            </thead>
            <tbody>
              ${exps.slice(0, 5).map(e => `
                <tr>
                  <td><span style="font-weight: 600; color: var(--accent-primary);">${escapeHtml(e.country)}</span></td>
                  <td><span style="font-size: 0.74rem; background: var(--bg-primary); padding: 2px 7px; border-radius: 3px; border: 1px solid var(--border-subtle);">${escapeHtml(e.domain)}</span></td>
                  <td>${escapeHtml(e.title)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  `;
}

/**
 * ===================================================================
 * TRANG 05: SỬ DỤNG HỆ THỐNG (PRODUCT USAGE) (05 / 05)
 * CÁC BIỂU ĐỒ ĐA DẠNG:
 * - SVG Area Trend Chart (Xu hướng tin nhắn RAG)
 * - Vertical Column Chart (Phân bổ theo số ngày hoạt động)
 * - Clustered Bar Chart (Thẻ kiểm chuẩn được trích xuất)
 * ===================================================================
 */
function renderAiscProductPage() {
  const data = (AISC_DASHBOARD_DATA.aiscReportData && AISC_DASHBOARD_DATA.aiscReportData.productUsage) || {};
  const kpis = data.kpis || { identified_questioners: 84, user_messages: 156, anonymous_messages: 42, returning_questioners: 29 };
  const cardUsage = data.botCardUsage || [];
  const activeDays = data.activeDays || [];
  const trends = data.messageTrend || [];

  const activeDaysColItems = activeDays.map(d => ({
    label: d.day_group,
    count: d.count,
    displayVal: `${d.count} (${d.pct}%)`
  }));

  return `
    <div class="pbi-cards-grid">
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.identified_questioners}</div>
        <div class="pbi-card-label">Identified Questioner</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.user_messages}</div>
        <div class="pbi-card-label">User Message</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.anonymous_messages}</div>
        <div class="pbi-card-label">Anonymous User Message</div>
      </div>
      <div class="pbi-card-visual">
        <div class="pbi-card-callout">${kpis.returning_questioners}</div>
        <div class="pbi-card-label">Returning Questioner</div>
      </div>
    </div>

    <!-- HÀNG 1: SVG Area Chart & Vertical Column Chart -->
    <div class="pbi-charts-grid">
      <!-- Visual 1: SVG Area Trend Chart -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Lưu lượng tin nhắn hỏi đáp RAG theo tháng (Area Trend)</div>
        </div>
        ${renderSvgAreaTrendChart(trends)}
      </div>

      <!-- Visual 2: Vertical Column Chart -->
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">Phân bổ người hỏi theo số ngày hoạt động (Column Chart)</div>
        </div>
        ${renderVerticalColumnChart(activeDaysColItems, 'count', 'label', 65, 'ocean')}
      </div>
    </div>

    <!-- HÀNG 2: Clustered Bar Chart -->
    <div class="pbi-chart-visual" style="margin-top: 1rem;">
      <div class="pbi-chart-header">
        <div class="pbi-chart-title">Thẻ kiểm chuẩn được trích xuất nhiều nhất</div>
      </div>
      <div class="pbi-bars-container">
        ${cardUsage.map(cu => `
          <div class="pbi-bar-row" title="${escapeHtml(cu.card_id)}">
            <div class="pbi-bar-label">${escapeHtml(cu.name)}</div>
            <div class="pbi-bar-track-wrap">
              <div class="pbi-bar-track">
                <div class="pbi-bar-fill" style="width: ${cu.count * 1.8}%; background: var(--accent-primary);"></div>
              </div>
              <div class="pbi-bar-val">${cu.count} lượt</div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  </div>
  `;
}

// Khởi chạy khi tài liệu tải xong
document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});
