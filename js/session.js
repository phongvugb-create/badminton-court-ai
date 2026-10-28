/* Tab-specific session locator; authentication tokens remain in HttpOnly cookies.
 * sessionStorage isolates accounts between tabs without putting JWTs in JS/URLs.
 */
window.BadmintonSession = (() => {
  const key = 'badminton_tab_session_v1';
  function read() {
    try {
      const value = JSON.parse(sessionStorage.getItem(key) || 'null');
      return value && /^[A-Za-z0-9_-]{16,64}$/.test(value.id) ? value : null;
    } catch { return null; }
  }
  return {
    id: () => read()?.id || null,
    user: () => read()?.user || null,
    headers: () => read() ? { 'X-Tab-Session': read().id } : {},
    save(data) {
      if (!data?.tab_session_id || !data.user) throw new Error('Máy chủ chưa tạo phiên riêng cho tab. Vui lòng cập nhật backend.');
      sessionStorage.setItem(key, JSON.stringify({ id: data.tab_session_id, user: data.user }));
    },
    clear: () => sessionStorage.removeItem(key),
    eventsUrl(url) {
      const id = read()?.id;
      return id ? `${url}?tab_session=${encodeURIComponent(id)}` : url;
    }
  };
})();
