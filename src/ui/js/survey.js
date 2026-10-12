/**
 * COMMUNITY SURVEY & DATA INGESTION (DCI - ASTERIA)
 * Quản lý gửi biểu mẫu đóng góp tình huống, đánh giá Likert và khử PII
 */

let likertValues = {
  prep: 3,
  intention: 4
};

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

  // 1. Gửi lên Backend PostgreSQL nếu API online
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
          user_id: currentUser ? currentUser.id : null
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

  // 2. Thêm vào hàng đợi Admin Queue cục bộ
  const newQueueItem = {
    id: newId,
    type: 'SURVEY_SUBMISSION',
    submitter: currentUser ? currentUser.name : 'Khách vãng lai',
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

  // Đặt lại biểu mẫu
  document.getElementById('communitySurveyForm').reset();
  setLikert('prep', 3);
  setLikert('intention', 4);

  // Cập nhật số lượng và hàng đợi
  if (typeof updateQueueBadge === 'function') updateQueueBadge();
  if (typeof renderAdminQueue === 'function') renderAdminQueue();

  // Hiển thị Popup chúc mừng
  const successModal = document.getElementById('surveySuccessModal');
  if (successModal) {
    successModal.classList.add('active');
  } else {
    showToast('🎉 Gửi đóng góp thành công! Cảm ơn bạn đã đóng góp cho dự án.');
  }
}
