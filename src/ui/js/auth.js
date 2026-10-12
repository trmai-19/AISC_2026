/**
 * AUTHENTICATION & ACCESS CONTROL (DCI - ASTERIA)
 * Quản lý phiên làm việc, đăng nhập, đăng ký, đăng xuất và phân quyền
 */

let currentUserRole = 'GUEST'; // 'GUEST' | 'USER' | 'ADMIN'
let currentUser = null;

const ROLE_CONFIGS = {
  GUEST: { label: 'Khách', badgeClass: 'guest' },
  USER: { label: 'Thành viên', badgeClass: '' },
  ADMIN: { label: 'Ban Quản Trị', badgeClass: 'admin' }
};

function initAuth() {
  const savedUser = localStorage.getItem('dci_user');
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      currentUserRole = currentUser.role || 'USER';
    } catch (e) {
      currentUser = null;
      currentUserRole = 'GUEST';
    }
  } else {
    // Mặc định ban đầu chưa đăng nhập (Khách vãng lai)
    currentUser = null;
    currentUserRole = 'GUEST';
  }
  applyRoleUI();
}

// Cập nhật giao diện thanh Header theo tài khoản hiện tại
function applyRoleUI() {
  const loginBtn = document.getElementById('headerLoginBtn');
  const profileBtn = document.getElementById('headerProfileBtn');
  const avatarText = document.getElementById('headerAvatarText');
  const userName = document.getElementById('headerUserName');
  const userRoleBadge = document.getElementById('headerUserRoleBadge');

  const isLoggedIn = currentUserRole !== 'GUEST' && currentUser && currentUser.name;

  if (loginBtn) {
    loginBtn.style.display = isLoggedIn ? 'none' : 'inline-flex';
  }

  if (profileBtn) {
    profileBtn.style.display = isLoggedIn ? 'inline-flex' : 'none';
    if (isLoggedIn) {
      if (avatarText) {
        avatarText.textContent = currentUser.name.trim().charAt(0).toUpperCase() || 'U';
      }
      if (userName) {
        userName.textContent = currentUser.name;
      }
      if (userRoleBadge) {
        const isAdmin = currentUserRole === 'ADMIN';
        userRoleBadge.textContent = isAdmin ? 'Admin' : 'Thành viên';
        userRoleBadge.className = `user-role-badge ${isAdmin ? 'admin' : ''}`.trim();
      }
    }
  }

  // Quản lý hiển thị tab Quản Trị (Chỉ hiển thị khi đăng nhập vai trò ADMIN)
  const adminTabBtn = document.getElementById('tab-btn-admin');
  const isAdmin = currentUserRole === 'ADMIN';
  if (adminTabBtn) {
    adminTabBtn.style.display = isAdmin ? 'inline-flex' : 'none';
  }

  // Nếu không phải Quản trị viên mà đang ở màn hình admin -> tự động chuyển về chat
  if (!isAdmin && typeof currentView !== 'undefined' && currentView === 'admin') {
    if (typeof switchView === 'function') {
      switchView('chat');
    }
  }

  // Hỗ trợ nút đăng nhập / đăng xuất cũ nếu có trên giao diện
  const authActionBtn = document.getElementById('headerAuthActionBtn');
  if (authActionBtn) {
    if (!isLoggedIn) {
      authActionBtn.textContent = 'Đăng nhập';
      authActionBtn.onclick = () => window.location.href = 'login.html';
    } else {
      authActionBtn.textContent = 'Đăng xuất';
      authActionBtn.onclick = logoutUser;
    }
  }
}

// Mở modal thông tin hồ sơ người dùng
function openProfileModal() {
  if (!currentUser) {
    window.location.href = 'login.html';
    return;
  }
  const modal = document.getElementById('userProfileModal');
  if (!modal) return;

  const avatar = document.getElementById('profileModalAvatar');
  const name = document.getElementById('profileModalName');
  const role = document.getElementById('profileModalRole');
  const email = document.getElementById('profileModalEmail');
  const country = document.getElementById('profileModalCountry');
  const purpose = document.getElementById('profileModalPurpose');

  if (avatar) avatar.textContent = currentUser.name.trim().charAt(0).toUpperCase() || 'U';
  if (name) name.textContent = currentUser.name || 'Người dùng';
  if (role) {
    const isAdmin = currentUserRole === 'ADMIN';
    role.textContent = isAdmin ? 'Ban Quản Trị (Admin)' : 'Thành viên';
    role.className = `user-role-badge ${isAdmin ? 'admin' : ''}`.trim();
  }
  if (email) email.textContent = currentUser.email || 'Chưa cập nhật email';

  const countryMap = { JP: '🇯🇵 Nhật Bản', KR: '🇰🇷 Hàn Quốc', AU: '🇦🇺 Australia' };
  const purposeMap = { DU_HOC: 'Du học sinh', LAO_DONG: 'Lao động kỹ năng', DINH_CU: 'Định cư dài hạn' };

  if (country) {
    const c = (currentUser.profile && currentUser.profile.target_country) || 'JP';
    country.textContent = countryMap[c] || 'Nhật Bản';
  }
  if (purpose) {
    const p = (currentUser.profile && currentUser.profile.purpose) || 'DU_HOC';
    purpose.textContent = purposeMap[p] || 'Du học sinh';
  }

  modal.classList.add('active');
}

function logoutFromProfileModal() {
  closeModal('userProfileModal');
  logoutUser();
}

// Kiểm tra quyền truy cập theo từng màn hình
function checkViewPermissions(viewId) {
  // Quyền truy cập trang Admin: chỉ dành cho role ADMIN
  if (viewId === 'admin' && currentUserRole !== 'ADMIN') {
    if (typeof switchView === 'function') {
      switchView('chat');
    }
    return false;
  }
  return true;
}

// Đăng nhập tài khoản qua API thực tế
async function loginUser(email, password) {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (res.ok) {
      const data = await res.json();
      currentUser = {
        id: data.user_id,
        name: data.full_name,
        email: data.email,
        role: data.role
      };
      currentUserRole = data.role;
      localStorage.setItem('dci_user', JSON.stringify(currentUser));
      return { success: true, user: currentUser };
    } else {
      const err = await res.json().catch(() => ({}));
      return { success: false, message: err.detail || 'Email hoặc mật khẩu không chính xác.' };
    }
  } catch (e) {
    return { success: false, message: 'Không thể kết nối đến máy chủ xác thực. Vui lòng kiểm tra dịch vụ Backend.' };
  }
}

// Đăng ký tài khoản mới qua API thực tế
async function registerUser(formData) {
  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    if (res.ok) {
      const data = await res.json();
      currentUser = {
        id: data.user_id,
        name: data.full_name,
        email: data.email,
        role: data.role,
        profile: {
          target_country: formData.target_country,
          purpose: formData.purpose
        }
      };
      currentUserRole = data.role;
      localStorage.setItem('dci_user', JSON.stringify(currentUser));
      return { success: true, user: currentUser };
    } else {
      const err = await res.json().catch(() => ({}));
      return { success: false, message: err.detail || 'Đăng ký không thành công. Email có thể đã tồn tại.' };
    }
  } catch (e) {
    return { success: false, message: 'Không thể kết nối đến máy chủ đăng ký. Vui lòng kiểm tra dịch vụ Backend.' };
  }
}

// Đăng xuất tài khoản
function logoutUser() {
  currentUserRole = 'GUEST';
  currentUser = null;
  localStorage.removeItem('dci_user');
  applyRoleUI();
  if (typeof checkViewPermissions === 'function') {
    checkViewPermissions(currentView);
  }
  showToast('Đã đăng xuất tài khoản thành công!');
}
