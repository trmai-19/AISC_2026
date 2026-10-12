/**
 * ADMIN SERVICE & APPROVAL QUEUE (DCI - ASTERIA)
 * Quản lý hàng đợi kiểm duyệt, lịch sử đã xử lý, phê duyệt & thăng cấp thẻ
 */

let currentAdminQueueTab = 'PENDING'; // 'PENDING' | 'PROCESSED'
let adminProcessedSubfilter = 'ALL';  // 'ALL' | 'APPROVED' | 'REJECTED'

function updateQueueBadge() {
  const pendingCount = APP_DATA.adminQueue.filter(item => item.status === 'PENDING').length;
  const approvedCount = APP_DATA.adminQueue.filter(item => item.status !== 'PENDING').length;

  const badge = document.getElementById('pendingQueueCount');
  const adminPendingStat = document.getElementById('adminPendingStat');
  const adminApprovedStat = document.getElementById('adminApprovedStat');
  const adminCardsStat = document.getElementById('adminCardsCountStat');

  if (badge) badge.textContent = pendingCount;
  if (adminPendingStat) adminPendingStat.textContent = pendingCount;
  if (adminApprovedStat) adminApprovedStat.textContent = approvedCount;
  if (adminCardsStat) adminCardsStat.textContent = APP_DATA.evidenceCards.length;
}

function switchAdminQueueView(tab) {
  currentAdminQueueTab = tab;

  const pendingCard = document.getElementById('adminFilterCardPending');
  const approvedCard = document.getElementById('adminFilterCardApproved');
  if (pendingCard) pendingCard.classList.toggle('active', tab === 'PENDING');
  if (approvedCard) approvedCard.classList.toggle('active', tab === 'PROCESSED');

  const subfilterToolbar = document.getElementById('adminProcessedSubfilters');
  const sectionTitle = document.getElementById('adminQueueSectionTitle');

  if (tab === 'PENDING') {
    if (subfilterToolbar) subfilterToolbar.style.display = 'none';
    if (sectionTitle) {
      sectionTitle.innerHTML = `
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        Hàng Đợi Chờ Duyệt (Pending Queue)
      `;
    }
  } else {
    if (subfilterToolbar) subfilterToolbar.style.display = 'flex';
    if (sectionTitle) {
      sectionTitle.innerHTML = `
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
        Lịch Sử Đã Xử Lý (Processed Items)
      `;
    }
  }

  renderAdminQueue();
}

function setAdminProcessedSubfilter(filter) {
  adminProcessedSubfilter = filter;
  document.querySelectorAll('.queue-subfilter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === `subfilter-${filter.toLowerCase()}`);
  });
  renderAdminQueue();
}

async function renderAdminQueue() {
  const container = document.getElementById('adminQueueContainer');
  if (!container) return;

  let itemsToDisplay = [];

  try {
    const params = new URLSearchParams();
    params.append('status', currentAdminQueueTab);
    if (currentAdminQueueTab === 'PROCESSED' && adminProcessedSubfilter !== 'ALL') {
      params.append('subfilter', adminProcessedSubfilter);
    }
    const res = await fetch(`${API_BASE}/admin/queue?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      itemsToDisplay = data.map(item => ({
        id: item.id,
        country: item.country,
        countryName: item.country_name,
        domainId: item.domain_id,
        domainName: item.domain_name,
        submittedAt: item.submitted_at,
        title: item.title,
        experienceText: item.experience_text,
        submitter: item.submitter,
        sourceCredibility: item.source_credibility,
        status: item.status
      }));
    }
  } catch (err) {
    console.warn('Admin queue API fetch error:', err);
  }

  // Cập nhật số lượng trên badge
  const badge = document.getElementById('pendingQueueCount');
  const adminPendingStat = document.getElementById('adminPendingStat');
  if (currentAdminQueueTab === 'PENDING') {
    if (badge) badge.textContent = itemsToDisplay.length;
    if (adminPendingStat) adminPendingStat.textContent = itemsToDisplay.length;
  }

  if (itemsToDisplay.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.9rem;">
        ${currentAdminQueueTab === 'PENDING' ? '✓ Hiện không có mục nào đang chờ duyệt trong hàng đợi.' : 'Chưa có mục nào phù hợp trong danh sách đã xử lý.'}
      </div>
    `;
    return;
  }

  container.innerHTML = itemsToDisplay.map(item => `
    <div class="queue-card-item">
      <div class="queue-header-meta">
        <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
          <span style="font-weight: 700; color: var(--text-primary);">${item.id}</span>
          <span class="badge-country">${item.countryName}</span>
          <span class="badge-domain">${item.domainName}</span>
          <span style="color: var(--text-muted); font-size: 0.74rem;">• ${item.submittedAt}</span>
        </div>
        <span class="badge-status ${item.status === 'PENDING' ? 'badge-pending' : (item.status === 'APPROVED' ? 'badge-approved' : 'badge-rejected')}">
          ${item.status === 'PENDING' ? 'Chờ duyệt' : (item.status === 'APPROVED' ? 'Đã phê duyệt' : 'Đã từ chối')}
        </span>
      </div>

      <div>
        <h4 style="font-size: 0.95rem; color: var(--text-primary); margin-bottom: 0.25rem;">${escapeHtml(item.title)}</h4>
        <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">${escapeHtml(item.experienceText)}</p>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.35rem;">
          Người gửi: <em>${escapeHtml(item.submitter)}</em> | Thẩm định: <em>${escapeHtml(item.sourceCredibility)}</em>
        </div>
      </div>

      ${item.status === 'PENDING' ? `
        <div class="queue-actions">
          <button class="btn-reject" onclick="processQueueItem('${item.id}', 'REJECT')">
            ✕ Từ chối
          </button>
          <button class="btn-approve" onclick="processQueueItem('${item.id}', 'APPROVE')">
            ✓ Phê duyệt
          </button>
        </div>
      ` : ''}
    </div>
  `).join('');
}

async function processQueueItem(itemId, action) {
  if (currentUserRole !== 'ADMIN' || !currentUser) {
    showToast('Vui lòng đăng nhập tài khoản Quản trị viên để thực hiện thao tác duyệt.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/admin/queue/${itemId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: action,
        admin_user_id: currentUser.id
      })
    });

    if (res.ok) {
      const data = await res.json();
      showToast(data.message || `Đã ${action === 'APPROVE' ? 'phê duyệt' : 'từ chối'} thành công!`);
      renderAdminQueue();
      if (typeof filterEvidenceCards === 'function') filterEvidenceCards();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || 'Thao tác duyệt không thành công.');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi gửi yêu cầu duyệt.');
  }
}
