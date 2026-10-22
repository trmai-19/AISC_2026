/**
 * CHATBOT RAG PIPELINE & INTERACTIONS (DCI - ASTERIA)
 * Quản lý hội thoại Copilot, trích dẫn bằng chứng và đánh giá phản hồi
 */

let userContext = {
  country: 'JP',
  purpose: 'DU_HOC',
  stage: 'PREPARING'
};

const DCI_ICON_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`;

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

  const chatContextLabel = document.getElementById('chatContextActiveLabel');
  if (chatContextLabel) {
    chatContextLabel.textContent = `Ngữ cảnh: ${countryObj.name} • ${purposeLabel} • ${stageLabel}`;
  }

  initSamplePrompts();
}

function initSamplePrompts() {
  const container = document.getElementById('samplePromptContainer');
  if (!container) return;

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

async function sendUserMessage() {
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return;

  appendMessage({ sender: 'user', text: query });
  input.value = '';

  const pipelineStatus = document.getElementById('ragPipelineStatus');
  if (pipelineStatus) pipelineStatus.textContent = 'Đang truy vấn pgvector & RAG...';

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 35000);

    const res = await fetch(`${API_BASE}/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        country: userContext.country,
        purpose: userContext.purpose,
        stage: userContext.stage,
        user_id: currentUser ? currentUser.id : null
      }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const apiData = await res.json();
      const responseData = mapBackendRagResponse(apiData);
      appendMessage({ sender: 'bot', ragData: responseData });
      if (pipelineStatus) pipelineStatus.textContent = 'Trực tuyến (Live pgvector)';
    } else {
      const err = await res.json().catch(() => ({}));
      appendMessage({
        sender: 'bot',
        ragData: {
          success: false,
          refusalMessage: err.detail || 'Máy chủ AI trả về lỗi trong quá trình xử lý câu hỏi.'
        }
      });
      if (pipelineStatus) pipelineStatus.textContent = 'Lỗi phản hồi';
    }
  } catch (err) {
    appendMessage({
      sender: 'bot',
      ragData: {
        success: false,
        refusalMessage: 'Không thể kết nối đến máy chủ AI Copilot. Vui lòng đảm bảo dịch vụ Backend đang hoạt động.'
      }
    });
    if (pipelineStatus) pipelineStatus.textContent = 'Ngoại tuyến';
  }
}

function mapBackendRagResponse(apiData) {
  if (apiData.direct_message) {
    return {
      success: true,
      responseType: apiData.response_type || 'GREETING',
      directMessage: apiData.direct_message
    };
  }

  if (!apiData.success || !apiData.matched_card) {
    return {
      success: false,
      responseType: apiData.response_type || 'OUT_OF_SCOPE',
      refusalMessage: apiData.refusal_message || "Câu hỏi này hiện không thuộc phạm vi thông tin và quy chuẩn văn hóa mà hệ thống DCI cung cấp."
    };
  }

  const card = apiData.matched_card;
  const countryMap = { JP: 'Nhật Bản', KR: 'Hàn Quốc', AU: 'Australia' };
  const countryName = card.country_name || countryMap[card.country_code] || card.country_code;

  return {
    success: true,
    responseType: 'RAG',
    card: {
      id: card.card_id,
      country: card.country_code,
      countryName: countryName,
      domainId: card.domain_id,
      domainName: card.domain_name || card.domain_id,
      title: card.title,
      context: card.context || `Bối cảnh tại ${countryName}`,
      verifiedContent: card.verified_content,
      safeAction: card.safe_action || apiData.safe_action,
      donots: card.donots || apiData.donots,
      organization: card.organization_name || (card.source && card.source.organization_name) || 'Cơ quan thẩm quyền',
      sourceType: (card.source && card.source.source_type) || 'Chuẩn mực chính thống',
      verifiedDate: card.verified_date,
      reliabilityScore: card.reliability_score || Math.round(apiData.confidence || 95)
    },
    contextAnalysis: apiData.context_analysis || `Bối cảnh thuộc lĩnh vực "${card.domain_id}" tại ${countryName}.`,
    safeAction: apiData.safe_action || card.safe_action,
    donots: apiData.donots || card.donots,
    confidence: apiData.confidence || card.reliability_score,
    confidenceLevel: card.confidence_level || 'Đã xác minh'
  };
}

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
    if (ragData && ragData.directMessage) {
      row.innerHTML = `
        <div class="message-avatar">${DCI_ICON_SVG}</div>
        <div class="message-bubble">
          <p style="margin: 0; line-height: 1.6; font-size: 0.92rem; color: var(--text-primary); white-space: pre-wrap;">${escapeHtml(ragData.directMessage)}</p>
        </div>
      `;
    } else if (ragData && ragData.success && ragData.card) {
      const card = ragData.card;
      row.innerHTML = `
        <div class="message-avatar">${DCI_ICON_SVG}</div>
        <div class="message-bubble">
          <div class="rag-response-card">
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

            <div class="rag-section-block block-context">
              <h4>1. Phân tích bối cảnh & Ngữ cảnh văn hóa</h4>
              <p>${escapeHtml(ragData.contextAnalysis)}</p>
              <p style="margin-top: 0.35rem; font-size: 0.82rem; opacity: 0.95;"><strong>Thực tế kiểm chứng:</strong> ${escapeHtml(card.verifiedContent)}</p>
            </div>

            <div class="rag-section-block block-safe">
              <h4>2. Hành vi ứng xử an toàn được đề xuất</h4>
              <p>${escapeHtml(ragData.safeAction)}</p>
            </div>

            <div class="rag-section-block block-donot">
              <h4>3. Điều tuyệt đối cần tránh (Don'ts)</h4>
              <p>${escapeHtml(ragData.donots)}</p>
            </div>

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

            <div class="rag-footer-row">
              <div class="chat-feedback-actions">
                <span style="font-size: 0.75rem; color: var(--text-muted); margin-right: 2px;">Đánh giá:</span>
                <button class="btn-feedback" onclick="handleFeedback(this, 'like')">👍 Hữu ích</button>
                <button class="btn-feedback" onclick="handleFeedback(this, 'report', '${card.id}')">🚩 Báo lỗi</button>
              </div>

              <button class="btn-copy-response" onclick="copyResponse(this)" title="Sao chép nội dung ứng xử an toàn">
                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span>Sao chép</span>
              </button>
            </div>
          </div>
        </div>
      `;
    } else {
      row.innerHTML = `
        <div class="message-avatar">${DCI_ICON_SVG}</div>
        <div class="message-bubble">
          <div style="border-left: 3px solid var(--accent-amber); padding-left: 0.75rem;">
            <strong style="color: var(--accent-amber); display: block; margin-bottom: 0.35rem; font-size: 0.88rem;">Ngoài phạm vi thông tin cung cấp</strong>
            <p style="margin: 0; line-height: 1.5; font-size: 0.88rem; color: var(--text-secondary);">${escapeHtml(ragData.refusalMessage)}</p>
          </div>
        </div>
      `;
    }
  }

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function copyResponse(btn) {
  const card = btn.closest('.rag-response-card');
  if (!card) return;
  const safeBlock = card.querySelector('.block-safe p');
  const textToCopy = safeBlock ? safeBlock.innerText : card.innerText;

  navigator.clipboard.writeText(textToCopy).then(() => {
    btn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg><span>Đã chép</span>`;
    showToast('Đã sao chép hành vi ứng xử an toàn vào clipboard!');
    setTimeout(() => {
      btn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>Sao chép</span>`;
    }, 2000);
  }).catch(() => {
    showToast('Sao chép thành công!');
  });
}

function handleFeedback(btn, type, cardId) {
  const parent = btn.parentElement;
  const likeBtn = parent.querySelector('.btn-feedback:first-of-type');
  const reportBtn = parent.querySelector('.btn-feedback:last-of-type');

  if (type === 'like') {
    if (btn.classList.contains('liked')) {
      btn.classList.remove('liked');
      btn.innerHTML = '👍 Hữu ích';
    } else {
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
      btn.classList.remove('reported');
      btn.innerHTML = '🚩 Báo lỗi';
    } else {
      btn.classList.add('reported');
      btn.innerHTML = '✓ Đã báo';
      if (likeBtn) {
        likeBtn.classList.remove('liked');
        likeBtn.innerHTML = '👍 Hữu ích';
      }

      if (isBackendConnected && cardId) {
        fetch(`${API_BASE}/chat/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            evidence_card_id: cardId,
            feedback_type: 'REPORT',
            user_id: currentUser ? currentUser.id : null
          })
        }).catch(err => console.warn('Sync feedback error:', err));
      }

      const ticketId = `REV-TKT-${Date.now().toString().slice(-4)}`;
      APP_DATA.adminQueue.unshift({
        id: ticketId,
        type: 'TICKET_FEEDBACK',
        submitter: `${currentUser ? currentUser.name : 'Thành viên'}`,
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

      if (typeof updateQueueBadge === 'function') updateQueueBadge();
      if (typeof renderAdminQueue === 'function') renderAdminQueue();
      showToast(`Đã gửi báo lỗi #${ticketId} vào hàng đợi kiểm duyệt!`);
    }
  }
}
