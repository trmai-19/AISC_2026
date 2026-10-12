/**
 * API SERVICE & HEALTH CHECK (DCI - ASTERIA)
 * Quản lý kết nối REST API tới FastAPI Backend
 */

const API_BASE = 'http://localhost:8000/api/v1';
let isBackendConnected = false;

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
    // Backend offline / standby
  }

  isBackendConnected = false;
  if (pill) pill.classList.remove('online');
  if (text) text.textContent = 'API: Standby (Mock)';
  return false;
}

// Wrapper gọi API có timeout an toàn
async function apiCall(endpoint, method = 'GET', body = null) {
  if (!isBackendConnected) return null;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal
    };
    if (body) options.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    clearTimeout(timeoutId);
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn(`Lỗi API [${method} ${endpoint}]:`, err);
  }
  return null;
}
