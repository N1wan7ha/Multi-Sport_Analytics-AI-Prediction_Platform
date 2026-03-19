export function setStatus(el, { type = 'info', message = '', show = true } = {}) {
  if (!el) return;
  if (!show || !message) {
    el.classList.add('d-none');
    el.textContent = '';
    return;
  }
  el.className = `alert alert-${type}`;
  el.textContent = message;
}

export function qs(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
}

export function getParam(name) {
  return new URLSearchParams(location.search).get(name);
}
