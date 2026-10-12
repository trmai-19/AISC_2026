/**
 * MAIN APP CONTROLLER & NAVIGATION (DCI - ASTERIA)
 * Điều phối ứng dụng, chuyển đổi màn hình, giao diện Sáng/Tối và Modals
 */

let currentView = 'chat';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Khởi tạo xác thực & người dùng
  if (typeof initAuth === 'function') initAuth();

  // 2. Khởi tạo các thành phần giao diện
  if (typeof initDomainFilters === 'function') initDomainFilters();
  if (typeof initSamplePrompts === 'function') initSamplePrompts();
  if (typeof renderEvidenceCards === 'function') renderEvidenceCards();
  if (typeof initSurveyDomainSelect === 'function') initSurveyDomainSelect();
  if (typeof renderAdminQueue === 'function') renderAdminQueue();
  if (typeof updateUserContext === 'function') updateUserContext();
  if (typeof updateQueueBadge === 'function') updateQueueBadge();

  // 3. Kiểm tra kết nối Backend FastAPI
  if (typeof checkBackendHealth === 'function') {
    checkBackendHealth();
    setInterval(checkBackendHealth, 10000);
  }

  // 4. Khởi tạo theme sáng/tối
  const savedTheme = localStorage.getItem('app-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
});

// Điều hướng màn hình
function switchView(viewId) {
  currentView = viewId;

  // Đổi view section
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
  const targetSection = document.getElementById(`view-${viewId}`);
  if (targetSection) targetSection.classList.add('active');

  // Đổi nút navbar
  document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
  const targetBtn = document.getElementById(`tab-btn-${viewId}`);
  if (targetBtn) targetBtn.classList.add('active');

  // Kiểm tra quyền truy cập (Role Guard)
  if (typeof checkViewPermissions === 'function') {
    checkViewPermissions(viewId);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Chuyển đổi Theme Sáng / Tối
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

// Điều khiển Modal
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function openInfoModal() {
  const modal = document.getElementById('projectInfoModal');
  if (modal) modal.classList.add('active');
}

// Hiển thị thông báo Toast
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
