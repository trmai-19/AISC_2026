/**
 * EVIDENCE EXPLORER & KNOWLEDGE HUB (DCI - ASTERIA)
 * Quản lý tra cứu Thẻ Bằng Chứng, bộ lọc đa tiêu chí và modal chi tiết
 */

let currentCountryFilter = 'ALL';
let currentDomainFilter = 'ALL';

function initDomainFilters() {
  const container = document.getElementById('domainFilterPills');
  if (!container) return;

  container.innerHTML = `
    <button class="domain-chip active" data-domain="ALL" onclick="setDomainFilter('ALL')">
      Tất cả
    </button>
  ` + APP_DATA.domains.map(d => `
    <button class="domain-chip" data-domain="${d.id}" onclick="setDomainFilter('${d.id}')">
      ${escapeHtml(d.name)}
    </button>
  `).join('');
}

function setCountryFilter(country) {
  currentCountryFilter = country;
  document.querySelectorAll('.filter-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.country === country);
  });
  filterEvidenceCards();
}

function setDomainFilter(domainId) {
  currentDomainFilter = domainId;
  document.querySelectorAll('.domain-chip').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.domain === domainId);
  });
  filterEvidenceCards();
}

let currentLoadedCards = APP_DATA.evidenceCards;

async function filterEvidenceCards() {
  const searchInput = document.getElementById('explorerSearchInput');
  const query = (searchInput ? searchInput.value : '').toLowerCase().trim();

  // 1. Nếu Backend online, tra cứu qua REST API
  if (isBackendConnected) {
    try {
      const params = new URLSearchParams();
      if (currentCountryFilter !== 'ALL') params.append('country', currentCountryFilter);
      if (currentDomainFilter !== 'ALL') params.append('domain', currentDomainFilter);
      if (query) params.append('q', query);

      const res = await fetch(`${API_BASE}/evidence?${params.toString()}`);
      if (res.ok) {
        const cards = await res.json();
        currentLoadedCards = cards.map(c => ({
          id: c.card_id,
          country: c.country_code,
          countryName: c.country_name,
          domainId: c.domain_id,
          domainName: c.domain_name,
          title: c.title,
          context: c.context,
          verifiedContent: c.verified_content,
          safeAction: c.safe_action,
          donots: c.donots,
          organization: c.organization_name || (c.source ? c.source.organization_name : 'Cơ quan thẩm quyền & Cộng đồng'),
          sourceType: c.source ? c.source.source_type : 'Kinh nghiệm đối soát cộng đồng',
          sourceUrl: c.source_url || (c.source ? c.source.document_url : '#'),
          reliabilityScore: c.reliability_score,
          verifiedDate: c.verified_date
        }));
        renderEvidenceCards(currentLoadedCards);
        return;
      }
    } catch (err) {
      console.warn('Evidence Hub API filter error, falling back to local data:', err);
    }
  }

  // 2. Chế độ dự phòng cục bộ
  currentLoadedCards = APP_DATA.evidenceCards.filter(card => {
    const matchCountry = currentCountryFilter === 'ALL' || card.country === currentCountryFilter;
    const matchDomain = currentDomainFilter === 'ALL' || card.domainId === currentDomainFilter;
    const matchQuery = !query || 
      card.title.toLowerCase().includes(query) ||
      card.context.toLowerCase().includes(query) ||
      card.verifiedContent.toLowerCase().includes(query) ||
      card.organization.toLowerCase().includes(query);

    return matchCountry && matchDomain && matchQuery;
  });

  renderEvidenceCards(currentLoadedCards);
}

function renderEvidenceCards(cards = currentLoadedCards) {
  const container = document.getElementById('evidenceCardsGrid');
  if (!container) return;

  if (!cards || cards.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px dashed var(--border-subtle);">
        <p style="color: var(--text-muted); font-size: 0.95rem;">Không tìm thấy thông tin phù hợp với bộ lọc hiện tại.</p>
        <button class="btn-card-action" style="margin: 0.75rem auto 0 auto;" onclick="resetExplorerFilters()">Đặt lại bộ lọc</button>
      </div>
    `;
    return;
  }

  container.innerHTML = cards.map(card => `
    <div class="evidence-card">
      <div>
        <div class="card-top-header">
          <div class="card-badges">
            <span class="badge-country">${card.countryName}</span>
            <span class="badge-domain">${card.domainName}</span>
          </div>
          <div class="badge-reliability">
            <svg width="12" height="12" fill="currentColor" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            ${card.reliabilityScore}%
          </div>
        </div>

        <h3 class="card-title" style="margin-top: 0.65rem;">${escapeHtml(card.title)}</h3>

        <div class="card-context-box" style="margin-top: 0.5rem;">
          <strong>Bối cảnh:</strong> ${escapeHtml(card.context)}
        </div>

        <p class="card-content-preview" style="margin-top: 0.6rem;">
          ${escapeHtml(card.verifiedContent)}
        </p>
      </div>

      <div class="card-footer">
        <div>
          <span style="display: block; font-weight: 600; color: var(--text-primary); font-size: 0.75rem;">${escapeHtml(card.organization)}</span>
          <span style="font-size: 0.7rem;">Xác minh: ${card.verifiedDate}</span>
        </div>
        <button class="btn-card-action" onclick="openEvidenceDetailModal('${card.id}')">
          Xem chi tiết
        </button>
      </div>
    </div>
  `).join('');
}

function resetExplorerFilters() {
  currentCountryFilter = 'ALL';
  currentDomainFilter = 'ALL';
  const searchInput = document.getElementById('explorerSearchInput');
  if (searchInput) searchInput.value = '';
  document.querySelectorAll('.filter-pill').forEach(btn => btn.classList.toggle('active', btn.dataset.country === 'ALL'));
  document.querySelectorAll('.domain-chip').forEach(btn => btn.classList.toggle('active', btn.dataset.domain === 'ALL'));
  filterEvidenceCards();
}

function openEvidenceDetailModal(cardId) {
  const card = currentLoadedCards.find(c => c.id === cardId) || APP_DATA.evidenceCards.find(c => c.id === cardId);
  if (!card) return;

  const modal = document.getElementById('evidenceDetailModal');
  const title = document.getElementById('modalCardTitle');
  const badges = document.getElementById('modalCardBadges');
  const body = document.getElementById('modalCardBody');

  if (title) title.textContent = card.title;
  if (badges) {
    badges.innerHTML = `
      <span class="badge-country">${card.countryName}</span>
      <span class="badge-domain">${card.domainName}</span>
      <span class="confidence-chip confidence-high">Mã: ${card.id} • Độ tin cậy: ${card.reliabilityScore}%</span>
    `;
  }

  if (body) {
    body.innerHTML = `
      <div class="card-context-box">
        <strong>Bối cảnh áp dụng:</strong> ${escapeHtml(card.context)}
      </div>

      <div>
        <h4 style="color: var(--accent-primary); font-size: 0.85rem; text-transform: uppercase; margin-bottom: 0.35rem; font-weight: 700;">Nội dung đã kiểm chứng (Verified Facts)</h4>
        <p style="font-size: 0.9rem; line-height: 1.55; color: var(--text-primary);">${escapeHtml(card.verifiedContent)}</p>
      </div>

      <div class="rag-section-block block-safe">
        <h4 style="margin-bottom: 0.3rem;">Hành vi ứng xử an toàn (Recommended Action):</h4>
        <p style="font-size: 0.85rem;">${escapeHtml(card.safeAction)}</p>
      </div>

      <div class="rag-section-block block-donot">
        <h4 style="margin-bottom: 0.3rem;">Điều tuyệt đối cần tránh (Don'ts):</h4>
        <p style="font-size: 0.85rem;">${escapeHtml(card.donots)}</p>
      </div>

      <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="color: var(--text-primary); font-weight: 700;">Nguồn: ${escapeHtml(card.organization)}</div>
          <div style="color: var(--text-muted);">Phân loại: ${escapeHtml(card.sourceType)} • Ngày xác minh: ${card.verifiedDate}</div>
        </div>
        ${card.sourceUrl ? `
          <a href="${card.sourceUrl}" target="_blank" rel="noopener" class="btn-card-action" style="text-decoration: none;">
            Xem tài liệu gốc ↗
          </a>
        ` : `
          <span style="font-size: 0.75rem; color: var(--accent-primary); background: var(--bg-surface); padding: 0.35rem 0.65rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-weight: 600;">
            ✓ Kinh nghiệm cộng đồng đối soát
          </span>
        `}
      </div>
    `;
  }

  if (modal) modal.classList.add('active');
}
