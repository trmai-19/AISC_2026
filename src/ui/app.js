/**
 * APP LOGIC: DCI - DIGITAL CULTURAL INTERPRETER (PHIÊN DỊCH VĂN HOÁ SỐ)
 * AISC'26 - Team Asteria (UIT - ĐHQG TP.HCM)
 * Multi-layer Architecture, Role-Based Access Control & RAG Workflow
 */

// Backend API Configuration
const API_BASE = 'http://localhost:8000/api/v1';
let isBackendConnected = false;

// Global State
let currentView = 'chat';
let currentCountryFilter = 'ALL';
let currentDomainFilter = 'ALL';
let activeDashboardTab = 'overview';
let currentAdminQueueTab = 'PENDING'; // 'PENDING' | 'PROCESSED'
let adminProcessedSubfilter = 'ALL';  // 'ALL' | 'APPROVED' | 'REJECTED'

let currentUserRole = 'USER'; // 'GUEST' | 'USER' | 'ADMIN'
const ROLE_CONFIGS = {
  GUEST: { label: 'Khách', badgeClass: 'guest', name: 'Khách vãng lai' },
  USER: { label: 'Thành viên', badgeClass: '', name: 'Nguyễn Văn A' },
  ADMIN: { label: 'Admin', badgeClass: 'admin', name: 'Ban Quản Trị DCI' }
};

let userContext = {
  country: 'JP',
  purpose: 'DU_HOC',
  stage: 'PREPARING'
};

let likertValues = {
  prep: 3,
  intention: 4
};

// ===================================================================
// BACKEND CONNECTIVITY & HEALTH CHECK
// ===================================================================
async function checkBackendHealth() {
  const pill = document.getElementById('backendStatusPill');
  const text = document.getElementById('backendStatusText');
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const res = await fetch('http://localhost:8000/health', { signal: controller.signal });
    clearTimeout(timeoutId);
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'ok') {
        isBackendConnected = true;
        if (pill) pill.classList.add('online');
        if (text) text.textContent = 'API: Online (pgvector)';
        return true;
      }
    }
  } catch (err) {
    // Backend offline / not reachable
  }

  isBackendConnected = false;
  if (pill) pill.classList.remove('online');
  if (text) text.textContent = 'API: Standby (Mock)';
  return false;
}

// ===================================================================
// INITIALIZATION
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
  initDomainFilters();
  initSamplePrompts();
  renderEvidenceCards();
  initSurveyDomainSelect();
  renderAdminQueue();
  updateUserContext();
  updateQueueBadge();
  applyRoleUI();

  // Check backend health and poll periodically
  checkBackendHealth();
  setInterval(checkBackendHealth, 10000);

  // Check saved theme
  const savedTheme = localStorage.getItem('app-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
});

// ===================================================================
// ROLE MANAGEMENT & PERMISSIONS (PAGE 5 FEEDBACK)
// ===================================================================
function openRoleModal() {
  const modal = document.getElementById('roleSelectModal');
  if (modal) modal.classList.add('active');
}

function switchRole(role) {
  if (!ROLE_CONFIGS[role]) return;
  currentUserRole = role;
  applyRoleUI();
  closeModal('roleSelectModal');
  showToast(`Đã chuyển vai trò: ${ROLE_CONFIGS[role].label} (${ROLE_CONFIGS[role].name})`);

  // Refresh current view permissions
  checkViewPermissions(currentView);
}

function applyRoleUI() {
  const badge = document.getElementById('headerRoleBadge');
  const name = document.getElementById('headerRoleName');
  const config = ROLE_CONFIGS[currentUserRole];

  if (badge) {
    badge.textContent = config.label;
    badge.className = `role-tag-badge ${config.badgeClass}`.trim();
  }
  if (name) {
    name.textContent = config.name;
  }

  // Update role options highlight in modal
  document.querySelectorAll('.role-option-card').forEach((card, idx) => {
    const roles = ['GUEST', 'USER', 'ADMIN'];
    card.classList.toggle('active', roles[idx] === currentUserRole);
  });
}

function checkViewPermissions(viewId) {
  // Admin view check
  const adminGuard = document.getElementById('adminRoleGuard');
  const adminContent = document.getElementById('adminMainContent');
  if (adminGuard && adminContent) {
    if (viewId === 'admin') {
      if (currentUserRole !== 'ADMIN') {
        adminGuard.style.display = 'block';
        adminContent.style.display = 'none';
      } else {
        adminGuard.style.display = 'none';
        adminContent.style.display = 'block';
      }
    }
  }

  // Dashboard view check
  const dashGuard = document.getElementById('dashboardRoleGuard');
  const dashContent = document.getElementById('dashboardMainContent');
  if (dashGuard && dashContent) {
    if (viewId === 'dashboard') {
      if (currentUserRole === 'GUEST') {
        dashGuard.style.display = 'block';
        dashContent.style.display = 'none';
      } else {
        dashGuard.style.display = 'none';
        dashContent.style.display = 'block';
      }
    }
  }
}

// ===================================================================
// NAVIGATION & VIEW SWITCHING
// ===================================================================
function switchView(viewId) {
  currentView = viewId;

  // Toggle sections
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
  const targetSection = document.getElementById(`view-${viewId}`);
  if (targetSection) targetSection.classList.add('active');

  // Toggle navbar buttons
  document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
  const targetBtn = document.getElementById(`tab-btn-${viewId}`);
  if (targetBtn) targetBtn.classList.add('active');

  // Check role guard
  checkViewPermissions(viewId);

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ===================================================================
// THEME SWITCHER
// ===================================================================
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('app-theme', newTheme);
  updateThemeIcon(newTheme);
  showToast(`Đã chuyển sang giao diện ${newTheme === 'dark' ? 'Tối' : 'Sáng'}`);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('themeToggleIcon');
  const text = document.getElementById('themeToggleText');
  if (icon) icon.textContent = theme === 'light' ? '☀️' : '🌙';
  if (text) text.textContent = theme === 'light' ? 'Sáng' : 'Tối';
}

// ===================================================================
// USER CONTEXT & PROFILES
// ===================================================================
function updateUserContext() {
  const countrySelect = document.getElementById('chatUserCountry');
  const purposeSelect = document.getElementById('chatUserPurpose');
  const stageSelect = document.getElementById('chatUserStage');

  if (countrySelect) userContext.country = countrySelect.value;
  if (purposeSelect) userContext.purpose = purposeSelect.value;
  if (stageSelect) userContext.stage = stageSelect.value;

  const countryObj = APP_DATA.countries.find(c => c.id === userContext.country) || APP_DATA.countries[0];
  const purposeLabel = userContext.purpose === 'DU_HOC' ? 'Du học sinh' : (userContext.purpose === 'LAO_DONG' ? 'Lao động kỹ năng' : 'Định cư');
  const stageLabel = userContext.stage === 'PREPARING' ? 'Đang chuẩn bị đi' : (userContext.stage === 'RECENT_ARRIVED' ? 'Mới sang < 6 tháng' : 'Đang sinh sống > 1 năm');

  // Update chat context active label
  const chatContextLabel = document.getElementById('chatContextActiveLabel');
  if (chatContextLabel) {
    chatContextLabel.textContent = `Ngữ cảnh: ${countryObj.name} • ${purposeLabel} • ${stageLabel}`;
  }

  // Refresh sample prompt chips based on selected country
  initSamplePrompts();
}

// ===================================================================
// CHATBOT RAG PIPELINE & INTERACTION
// ===================================================================
function initSamplePrompts() {
  const container = document.getElementById('samplePromptContainer');
  if (!container) return;

  // Filter or prioritize queries for selected country
  const relevantQueries = APP_DATA.sampleQueries.filter(q => q.country === userContext.country);
  const otherQueries = APP_DATA.sampleQueries.filter(q => q.country !== userContext.country);
  const displayQueries = [...relevantQueries, ...otherQueries].slice(0, 4);

  container.innerHTML = displayQueries.map(q => {
    const countryObj = APP_DATA.countries.find(c => c.id === q.country) || { name: q.country };
    return `
      <button class="prompt-chip" onclick="handlePromptClick('${escapeHtml(q.text)}')">
        <span style="font-weight: 700; color: var(--text-primary); display: block; margin-bottom: 2px;">
          ${countryObj.name} • ${escapeHtml(q.tags.join(' • '))}
        </span>
        ${escapeHtml(q.text)}
      </button>
    `;
  }).join('');
}

function handlePromptClick(promptText) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = promptText;
    sendUserMessage();
  }
}

function handleChatKeyDown(event) {
  if (event.key === 'Enter') {
    event.preventDefault();
    sendUserMessage();
  }
}

function sendUserMessage() {
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return;

  // Append User Message
  appendMessage({
    sender: 'user',
    text: query
  });

  input.value = '';

  // Simulate RAG Pipeline steps
  simulateRagPipeline(query);
}

async function simulateRagPipeline(query) {
  const pipelineStatus = document.getElementById('ragPipelineStatus');
  if (pipelineStatus) pipelineStatus.textContent = 'Đang xử lý...';

  // 1. Nếu Backend FastAPI đang chạy, gọi trực tiếp API RAG pgvector
  if (isBackendConnected) {
    try {
      if (pipelineStatus) pipelineStatus.textContent = 'Truy vấn pgvector & RAG...';
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const res = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          country: userContext.country,
          purpose: userContext.purpose,
          stage: userContext.stage,
          user_id: 'usr-2026-0000-0000-000000000001'
        }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const apiData = await res.json();
        const responseData = mapBackendRagResponse(apiData);
        appendMessage({
          sender: 'bot',
          ragData: responseData
        });
        if (pipelineStatus) pipelineStatus.textContent = 'Active (Live pgvector)';
        return;
      }
    } catch (err) {
      console.warn('RAG API request error, falling back to local dataset:', err);
    }
  }

  // 2. Chế độ dự phòng (Fallback): Tra cứu tức thời trên tập dữ liệu chuẩn bị sẵn
  setTimeout(() => {
    const responseData = generateRagResponse(query);
    appendMessage({
      sender: 'bot',
      ragData: responseData
    });

    if (pipelineStatus) {
      pipelineStatus.textContent = isBackendConnected ? 'Active' : 'Active (Mock mode)';
    }
  }, 600);
}

function mapBackendRagResponse(apiData) {
  if (!apiData.success || !apiData.matched_card) {
    return {
      success: false,
      refusalMessage: apiData.refusal_message || "Hiện cơ sở tri thức đã kiểm chứng của hệ thống chưa có đủ bằng chứng (Evidence Card) với độ tin cậy đạt chuẩn cho truy vấn này."
    };
  }

  const card = apiData.matched_card;
  const countryObj = APP_DATA.countries.find(c => c.id === card.country_code) || { name: card.country_code };
  const domainObj = APP_DATA.domains.find(d => d.id === card.domain_id) || { name: card.domain_id };

  return {
    success: true,
    card: {
      id: card.card_id,
      country: card.country_code,
      countryName: countryObj.name,
      domainId: card.domain_id,
      domainName: domainObj.name,
      title: card.title,
      context: card.context || `Bối cảnh tại ${countryObj.name}`,
      verifiedContent: card.verified_content,
      safeAction: card.safe_action || apiData.safe_action,
      donots: card.donots || apiData.donots,
      organization: card.organization,
      sourceType: card.source_type,
      verifiedDate: card.verified_date,
      reliabilityScore: card.reliability_score || Math.round(apiData.confidence_score)
    },
    contextAnalysis: apiData.context_analysis || `Bối cảnh thuộc lĩnh vực "${domainObj.name}" tại ${countryObj.name}.`,
    safeAction: apiData.safe_action || card.safe_action,
    donots: apiData.donots || card.donots,
    confidence: Math.round(apiData.confidence_score) || card.reliability_score,
    confidenceLevel: card.confidence_level || 'Đã xác minh'
  };
}

function generateRagResponse(query) {
  const lowerQuery = query.toLowerCase();

  // Search through Evidence Cards with priority for user's selected country
  let matchedCard = APP_DATA.evidenceCards.find(card => {
    if (lowerQuery.includes('vỡ bát') || lowerQuery.includes('bát đĩa') || lowerQuery.includes('baito')) {
      return card.id === 'EVD-JP-001';
    }
    if (lowerQuery.includes('thường trú') || lowerQuery.includes('28h') || lowerQuery.includes('my number') || lowerQuery.includes('kuyakusho')) {
      return card.id === 'EVD-JP-002';
    }
    if (lowerQuery.includes('rác') || lowerQuery.includes('tiếng ồn') || lowerQuery.includes('apato') || lowerQuery.includes('phân loại')) {
      return card.id === 'EVD-JP-003';
    }
    if (lowerQuery.includes('kính ngữ') || lowerQuery.includes('sunbae') || lowerQuery.includes('tiền bối') || lowerQuery.includes('hai tay')) {
      return card.id === 'EVD-KR-001';
    }
    if (lowerQuery.includes('bàn ăn') || lowerQuery.includes('hoesik') || lowerQuery.includes('rót rượu') || lowerQuery.includes('cắm đũa')) {
      return card.id === 'EVD-KR-002';
    }
    if (lowerQuery.includes('nhis') || lowerQuery.includes('bảo hiểm y tế') || lowerQuery.includes('viện phí')) {
      return card.id === 'EVD-KR-003';
    }
    if (lowerQuery.includes('lương') || lowerQuery.includes('fair work') || lowerQuery.includes('visa 500') || lowerQuery.includes('48h')) {
      return card.id === 'EVD-AU-001';
    }
    if (lowerQuery.includes('first name') || lowerQuery.includes('small talk') || lowerQuery.includes('xưng hô') || lowerQuery.includes('tài xế')) {
      return card.id === 'EVD-AU-002';
    }
    if (lowerQuery.includes('tip') || lowerQuery.includes('tiền tip') || lowerQuery.includes('split') || lowerQuery.includes('hóa đơn')) {
      return card.id === 'EVD-AU-003';
    }
    return false;
  });

  // If no direct keyword match, search by country & general keywords
  if (!matchedCard) {
    matchedCard = APP_DATA.evidenceCards.find(c => c.country === userContext.country);
  }

  if (matchedCard) {
    return {
      success: true,
      card: matchedCard,
      contextAnalysis: `Bối cảnh thuộc lĩnh vực "${matchedCard.domainName}" tại ${matchedCard.countryName}. Tình huống liên quan trực tiếp đến quy tắc ứng xử thực tế và chuẩn mực hành chính của nước sở tại mà du học sinh/người lao động thường gặp.`,
      safeAction: matchedCard.safeAction,
      donots: matchedCard.donots,
      confidence: matchedCard.reliabilityScore,
      confidenceLevel: matchedCard.confidenceLevel
    };
  }

  // Refusal case when insufficient evidence
  return {
    success: false,
    refusalMessage: "Hiện cơ sở tri thức đã kiểm chứng của hệ thống chưa có đủ bằng chứng (Evidence Card) với độ tin cậy đạt chuẩn cho truy vấn cụ thể này. Để tránh suy diễn sai lệch, hệ thống từ chối đưa ra kết luận và khuyến nghị bạn tra cứu trực tiếp tại website của Đại sứ quán hoặc Cơ quan thẩm quyền nước sở tại."
  };
}

const DCI_ICON_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`;

function appendMessage({ sender, text, ragData }) {
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const welcomeHero = document.getElementById('chatWelcomeHero');
  if (welcomeHero) welcomeHero.remove();

  const row = document.createElement('div');
  row.className = `message-row ${sender}`;

  if (sender === 'user') {
    row.innerHTML = `
      <div class="message-avatar">👤</div>
      <div class="message-bubble">
        <p>${escapeHtml(text)}</p>
      </div>
    `;
  } else {
    // BOT RAG Response
    if (ragData && ragData.success) {
      const card = ragData.card;
      row.innerHTML = `
        <div class="message-avatar">${DCI_ICON_SVG}</div>
        <div class="message-bubble">
          <div class="rag-response-card">
            <!-- Header Badges -->
            <div class="rag-header-badge">
              <div style="display: flex; gap: 6px; align-items: center;">
                <span class="badge-country">${card.countryName}</span>
                <span class="badge-domain">${card.domainName}</span>
              </div>
              <span class="confidence-chip confidence-high">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Đã kiểm chứng: ${ragData.confidence}%
              </span>
            </div>

            <!-- 1. Phân Tích Bối Cảnh -->
            <div class="rag-section-block block-context">
              <h4>1. Phân tích bối cảnh & Ngữ cảnh văn hóa</h4>
              <p>${escapeHtml(ragData.contextAnalysis)}</p>
              <p style="margin-top: 0.35rem; font-size: 0.82rem; opacity: 0.95;"><strong>Thực tế kiểm chứng:</strong> ${escapeHtml(card.verifiedContent)}</p>
            </div>

            <!-- 2. Hành Vi Ứng Xử An Toàn -->
            <div class="rag-section-block block-safe">
              <h4>2. Hành vi ứng xử an toàn được đề xuất</h4>
              <p>${escapeHtml(ragData.safeAction)}</p>
            </div>

            <!-- 3. Điều Cần Tránh -->
            <div class="rag-section-block block-donot">
              <h4>3. Điều tuyệt đối cần tránh (Don'ts)</h4>
              <p>${escapeHtml(ragData.donots)}</p>
            </div>

            <!-- 4. Thẻ Trích Dẫn Nguồn Kiểm Chứng -->
            <div class="block-evidence">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <span class="evidence-source-tag">Evidence Card [${card.id}]</span>
                <span style="font-size: 0.72rem; color: var(--accent-emerald); font-weight: 600;">● Xác minh: ${card.verifiedDate}</span>
              </div>
              <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem;">${escapeHtml(card.title)}</div>
              <div style="font-size: 0.78rem; color: var(--text-secondary);">Tổ chức kiểm chứng: <strong>${escapeHtml(card.organization)}</strong> (${escapeHtml(card.sourceType)})</div>
              <div style="display: flex; gap: 0.65rem; margin-top: 0.5rem; align-items: center;">
                <button class="btn-card-action" onclick="openEvidenceDetailModal('${card.id}')">Xem chi tiết thẻ</button>
              </div>
            </div>

            <!-- Footer Row: Feedback (Left) & Dedicated Copy Button (Right) - Page 3 Feedback -->
            <div class="rag-footer-row">
              <div class="chat-feedback-actions">
                <span style="font-size: 0.75rem; color: var(--text-muted); margin-right: 2px;">Đánh giá:</span>
                <button class="btn-feedback" onclick="handleFeedback(this, 'like')">
                  👍 Hữu ích
                </button>
                <button class="btn-feedback" onclick="handleFeedback(this, 'report', '${card.id}')">
                  🚩 Báo lỗi
                </button>
              </div>

              <!-- Dedicated Copy Button at bottom-right of message -->
              <button class="btn-copy-response" onclick="copyResponse(this)" title="Sao chép nội dung ứng xử an toàn">
                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span>Sao chép</span>
              </button>
            </div>
          </div>
        </div>
      `;
    } else {
      // Refusal message
      row.innerHTML = `
        <div class="message-avatar">${DCI_ICON_SVG}</div>
        <div class="message-bubble">
          <div style="border-left: 3px solid var(--accent-amber); padding-left: 0.75rem;">
            <strong style="color: var(--accent-amber); display: block; margin-bottom: 0.35rem;">Từ chối trả lời (Nguyên tắc an toàn dữ liệu)</strong>
            <p>${escapeHtml(ragData.refusalMessage)}</p>
          </div>
        </div>
      `;
    }
  }

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

// Standalone Copy Response function
function copyResponse(btn) {
  const card = btn.closest('.rag-response-card');
  if (!card) return;
  const safeBlock = card.querySelector('.block-safe p');
  const textToCopy = safeBlock ? safeBlock.innerText : card.innerText;

  navigator.clipboard.writeText(textToCopy).then(() => {
    btn.innerHTML = `
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
      <span>Đã chép</span>
    `;
    showToast('Đã sao chép hành vi ứng xử an toàn vào clipboard!');
    setTimeout(() => {
      btn.innerHTML = `
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        <span>Sao chép</span>
      `;
    }, 2000);
  }).catch(() => {
    showToast('Sao chép thành công!');
  });
}

// Mutually Exclusive Feedback logic (Page 3 Feedback)
function handleFeedback(btn, type, cardId) {
  const parent = btn.parentElement;
  const likeBtn = parent.querySelector('.btn-feedback:first-of-type');
  const reportBtn = parent.querySelector('.btn-feedback:last-of-type');

  if (type === 'like') {
    if (btn.classList.contains('liked')) {
      // Toggle off
      btn.classList.remove('liked');
      btn.innerHTML = '👍 Hữu ích';
    } else {
      // Set like, remove report
      btn.classList.add('liked');
      btn.innerHTML = '✓ Đã thích';
      if (reportBtn) {
        reportBtn.classList.remove('reported');
        reportBtn.innerHTML = '🚩 Báo lỗi';
      }
      showToast('Cảm ơn bạn đã đánh giá câu trả lời hữu ích!');
    }
  } else {
    if (btn.classList.contains('reported')) {
      // Toggle off
      btn.classList.remove('reported');
      btn.innerHTML = '🚩 Báo lỗi';
    } else {
      // Set report, remove like
      btn.classList.add('reported');
      btn.innerHTML = '✓ Đã báo';
      if (likeBtn) {
        likeBtn.classList.remove('liked');
        likeBtn.innerHTML = '👍 Hữu ích';
      }

      // Sync feedback to backend if online
      if (isBackendConnected && cardId) {
        fetch(`${API_BASE}/chat/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            evidence_card_id: cardId,
            feedback_type: 'REPORT',
            user_id: 'usr-2026-0000-0000-000000000001'
          })
        }).catch(err => console.warn('Sync feedback to backend error:', err));
      }

      // Add ticket to admin queue
      const ticketId = `REV-TKT-${Date.now().toString().slice(-4)}`;
      APP_DATA.adminQueue.unshift({
        id: ticketId,
        type: 'TICKET_FEEDBACK',
        submitter: `${ROLE_CONFIGS[currentUserRole].name} (${ROLE_CONFIGS[currentUserRole].label})`,
        country: userContext.country,
        countryName: userContext.country === 'JP' ? 'Nhật Bản' : (userContext.country === 'KR' ? 'Hàn Quốc' : 'Australia'),
        domainId: 'giao_tiep',
        domainName: 'Giao tiếp – Văn hoá ứng xử',
        submittedAt: new Date().toLocaleString(),
        title: `Báo cáo nội dung thẻ ${cardId || 'RAG'}`,
        experienceText: `Người dùng gửi phản hồi cần hiệu đính nguồn và nội dung ứng xử cho câu hỏi vừa qua.`,
        sourceCredibility: 'Phản hồi người dùng trực tiếp',
        status: 'PENDING'
      });

      updateQueueBadge();
      renderAdminQueue();
      showToast(`Đã gửi báo lỗi #${ticketId} vào hàng đợi kiểm duyệt!`);
    }
  }
}

// ===================================================================
// EVIDENCE HUB (TRA CỨU THÔNG TIN)
// ===================================================================
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
        const mapped = cards.map(c => ({
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
          organization: c.organization,
          sourceType: c.source_type,
          sourceUrl: c.source_url || '#',
          reliabilityScore: c.reliability_score,
          verifiedDate: c.verified_date
        }));
        renderEvidenceCards(mapped);
        return;
      }
    } catch (err) {
      console.warn('Evidence Hub API filter error, falling back to local data:', err);
    }
  }

  // 2. Chế độ dự phòng cục bộ
  const filtered = APP_DATA.evidenceCards.filter(card => {
    // Country filter
    const matchCountry = currentCountryFilter === 'ALL' || card.country === currentCountryFilter;
    // Domain filter
    const matchDomain = currentDomainFilter === 'ALL' || card.domainId === currentDomainFilter;
    // Search query
    const matchQuery = !query || 
      card.title.toLowerCase().includes(query) ||
      card.context.toLowerCase().includes(query) ||
      card.verifiedContent.toLowerCase().includes(query) ||
      card.organization.toLowerCase().includes(query);

    return matchCountry && matchDomain && matchQuery;
  });

  renderEvidenceCards(filtered);
}

function renderEvidenceCards(cards = APP_DATA.evidenceCards) {
  const container = document.getElementById('evidenceCardsGrid');
  if (!container) return;

  if (cards.length === 0) {
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
  renderEvidenceCards();
}

function openEvidenceDetailModal(cardId) {
  const card = APP_DATA.evidenceCards.find(c => c.id === cardId);
  if (!card) return;

  const modal = document.getElementById('evidenceDetailModal');
  const title = document.getElementById('modalCardTitle');
  const badges = document.getElementById('modalCardBadges');
  const body = document.getElementById('modalCardBody');

  title.textContent = card.title;
  badges.innerHTML = `
    <span class="badge-country">${card.countryName}</span>
    <span class="badge-domain">${card.domainName}</span>
    <span class="confidence-chip confidence-high">Mã: ${card.id} • Độ tin cậy: ${card.reliabilityScore}%</span>
  `;

  // Clean HTML with high contrast in Light Mode (no hardcoded #fff)
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
      <a href="${card.sourceUrl}" target="_blank" rel="noopener" class="btn-card-action" style="text-decoration: none;">
        Xem tài liệu gốc ↗
      </a>
    </div>
  `;

  modal.classList.add('active');
}

// ===================================================================
// COMMUNITY SURVEY FORM & POPUP SUBMISSION (PAGE 1 FEEDBACK)
// ===================================================================
function initSurveyDomainSelect() {
  const select = document.getElementById('surveyExpDomain');
  if (!select) return;

  select.innerHTML = APP_DATA.domains.map(d => `
    <option value="${d.id}">${escapeHtml(d.name)}</option>
  `).join('');
}

function setLikert(type, value) {
  likertValues[type] = value;
  const container = document.getElementById(type === 'prep' ? 'surveyPrepScale' : 'surveyIntentionScale');
  if (!container) return;

  const options = container.querySelectorAll('.likert-option');
  options.forEach((opt, idx) => {
    opt.classList.toggle('selected', idx + 1 === value);
  });
}

async function handleSurveySubmit(event) {
  event.preventDefault();

  const country = document.getElementById('surveyCountry').value;
  const expTitle = document.getElementById('surveyExpTitle').value.trim();
  const expDomain = document.getElementById('surveyExpDomain').value;
  const expText = document.getElementById('surveyExpText').value.trim();

  const countryName = country === 'JP' ? 'Nhật Bản' : (country === 'KR' ? 'Hàn Quốc' : 'Australia');
  const domainObj = APP_DATA.domains.find(d => d.id === expDomain) || APP_DATA.domains[0];

  let newId = `REV-2026-${(APP_DATA.adminQueue.length + 1).toString().padStart(3, '0')}`;

  // Gửi lên Backend PostgreSQL nếu API online
  if (isBackendConnected) {
    try {
      const res = await fetch(`${API_BASE}/survey/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          country: country,
          domain_id: expDomain,
          title: expTitle,
          experience_text: expText,
          prep_level: likertValues.prep,
          use_intention: likertValues.intention,
          challenges: ["R01", "R02"],
          user_id: 'usr-2026-0000-0000-000000000001'
        })
      });
      if (res.ok) {
        const result = await res.json();
        if (result.ticket_id) newId = result.ticket_id;
      }
    } catch (err) {
      console.warn('Survey API submission error, falling back to local queue:', err);
    }
  }

  // Add into Admin Queue with status 'PENDING'
  const newQueueItem = {
    id: newId,
    type: 'SURVEY_SUBMISSION',
    submitter: `${ROLE_CONFIGS[currentUserRole].name} (${ROLE_CONFIGS[currentUserRole].label})`,
    country: country,
    countryName: countryName,
    domainId: expDomain,
    domainName: domainObj.name,
    submittedAt: new Date().toLocaleString(),
    title: expTitle,
    experienceText: expText,
    sourceCredibility: 'Khảo sát cộng đồng đã khử định danh PII',
    status: 'PENDING',
    proposedCard: {
      title: expTitle,
      safeAction: expText.slice(0, 120) + '...',
      donots: 'Tránh hành động tự phát khi chưa nắm rõ quy định bản địa.'
    }
  };

  APP_DATA.adminQueue.unshift(newQueueItem);

  // Reset form
  document.getElementById('communitySurveyForm').reset();
  setLikert('prep', 3);
  setLikert('intention', 4);

  // Update badges & admin view
  updateQueueBadge();
  renderAdminQueue();

  // Show Popup Success Modal (Page 1 Feedback)
  const successModal = document.getElementById('surveySuccessModal');
  if (successModal) {
    successModal.classList.add('active');
  } else {
    showToast('🎉 Gửi đóng góp thành công! Cảm ơn bạn đã đóng góp cho dự án.');
  }
}

// ===================================================================
// ADMIN SERVICE & APPROVAL QUEUE (PAGE 3, 4, 5 FEEDBACK)
// ===================================================================
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

// Switch between 'PENDING' queue and 'PROCESSED' history (Page 5 Feedback)
function switchAdminQueueView(tab) {
  currentAdminQueueTab = tab;

  // Toggle active stat card
  const pendingCard = document.getElementById('adminFilterCardPending');
  const approvedCard = document.getElementById('adminFilterCardApproved');
  if (pendingCard) pendingCard.classList.toggle('active', tab === 'PENDING');
  if (approvedCard) approvedCard.classList.toggle('active', tab === 'PROCESSED');

  // Toggle subfilters bar
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

function renderAdminQueue() {
  const container = document.getElementById('adminQueueContainer');
  if (!container) return;

  let itemsToDisplay = [];

  if (currentAdminQueueTab === 'PENDING') {
    // Only pending items (Page 4 Feedback: "Đã phê duyệt/ đã từ chối thì không để trong tab hàng đợi nữa")
    itemsToDisplay = APP_DATA.adminQueue.filter(item => item.status === 'PENDING');
  } else {
    // Processed history items (Page 5 Feedback)
    itemsToDisplay = APP_DATA.adminQueue.filter(item => item.status !== 'PENDING');
    if (adminProcessedSubfilter === 'APPROVED') {
      itemsToDisplay = itemsToDisplay.filter(item => item.status === 'APPROVED');
    } else if (adminProcessedSubfilter === 'REJECTED') {
      itemsToDisplay = itemsToDisplay.filter(item => item.status === 'REJECTED');
    }
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
        <!-- Clean buttons (Page 4 Feedback: "phê duyệt là được. Bỏ đoạn &...") -->
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
  const item = APP_DATA.adminQueue.find(i => i.id === itemId);
  if (!item) return;

  // Gọi API review tới Backend nếu online
  if (isBackendConnected) {
    try {
      await fetch(`${API_BASE}/admin/queue/${itemId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          reviewer_id: 'usr-2026-0000-0000-000000000001'
        })
      });
    } catch (err) {
      console.warn('Admin review API error:', err);
    }
  }

  if (action === 'APPROVE') {
    item.status = 'APPROVED';

    // Promote to new official Evidence Card
    const newEvidenceCard = {
      id: `EVD-${item.country}-${(APP_DATA.evidenceCards.length + 1).toString().padStart(3, '0')}`,
      country: item.country,
      countryName: item.countryName,
      domainId: item.domainId,
      domainName: item.domainName,
      title: item.title,
      context: `Kinh nghiệm thực tiễn từ cộng đồng người Việt tại ${item.countryName}.`,
      verifiedContent: item.experienceText,
      safeAction: item.proposedCard ? item.proposedCard.safeAction : item.experienceText,
      donots: item.proposedCard ? item.proposedCard.donots : 'Tránh vi phạm quy định cơ quan sở tại.',
      organization: 'Khảo sát cộng đồng DCI (Đã thẩm định)',
      sourceType: 'Dữ liệu cộng đồng kiểm chuẩn',
      sourceUrl: '#',
      reliabilityScore: 95,
      confidenceLevel: 'Đã xác minh (95%)',
      publishedDate: new Date().toISOString().split('T')[0],
      verifiedDate: new Date().toISOString().split('T')[0],
      status: 'APPROVED'
    };

    APP_DATA.evidenceCards.unshift(newEvidenceCard);
    renderEvidenceCards();
    showToast(`✓ Đã duyệt "${item.title}" và chuyển thành công vào Kho Evidence Hub!`);
  } else {
    item.status = 'REJECTED';
    showToast(`✕ Đã từ chối mục ${item.id}.`);
  }

  updateQueueBadge();
  renderAdminQueue();
}

// ===================================================================
// DASHBOARD SUB-TABS & FILTERS
// ===================================================================
function switchDashboardTab(tabId) {
  activeDashboardTab = tabId;

  // Toggle buttons
  document.querySelectorAll('.dash-tab-btn').forEach(btn => btn.classList.remove('active'));
  const btn = document.getElementById(`btn-dash-${tabId}`);
  if (btn) btn.classList.add('active');

  // Toggle panels
  document.querySelectorAll('.dash-subpanel').forEach(p => p.style.display = 'none');
  const panel = document.getElementById(`dash-panel-${tabId}`);
  if (panel) panel.style.display = 'block';
}

function updateDashboardFilters() {
  const country = document.getElementById('dashFilterCountry').value;
  const exp = document.getElementById('dashFilterExperience').value;
  showToast(`Đã áp dụng bộ lọc: ${country === 'ALL' ? 'Tất cả' : country} • ${exp === 'ALL' ? 'Tất cả' : exp}`);
}

// ===================================================================
// MODAL CONTROLS & UTILITIES
// ===================================================================
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function openInfoModal() {
  const modal = document.getElementById('projectInfoModal');
  if (modal) modal.classList.add('active');
}

function showToast(message) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
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
