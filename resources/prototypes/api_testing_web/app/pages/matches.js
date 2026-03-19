import { fetchCricbuzzLive, fetchCricbuzzRecent, mapCricbuzzToMatches } from '../api/cricbuzz.js';
import { fetchCurrentMatches } from '../api/cricapi.js';
import { normalizeMatchFromCricApi } from '../domain/normalize.js';
import { mergeAndDedupeMatches } from '../domain/merge.js';
import { qs, setStatus } from '../ui/dom.js';

const el = {
  refreshBtn: qs('refreshBtn'),
  matchesList: qs('matchesList'),
  statusBar: document.getElementById('statusBar'),
  categoryFilter: qs('categoryFilter'),
  genderFilter: qs('genderFilter'),
  formatFilter: qs('formatFilter'),
  statusFilter: qs('statusFilter'),
  searchInput: qs('searchInput')
};

let allMatches = [];

function render(list) {
  if (!list.length) {
    el.matchesList.innerHTML = '<div class="text-body-secondary">No matches found.</div>';
    return;
  }

  el.matchesList.innerHTML = list
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')))
    .map((m) => {
      const badge = m.status === 'live' ? 'danger' : (m.status === 'complete' ? 'secondary' : 'success');
      const catBadge = m.category === 'franchise' ? 'warning' : 'info';
      const genderBadge = m.gender === 'women' ? 'primary' : 'dark';

      const t1 = m.teams?.[0]?.name || 'Team 1';
      const t2 = m.teams?.[1]?.name || 'Team 2';

      return `
        <div class="card">
          <div class="card-body">
            <div class="d-flex flex-wrap gap-2 align-items-center justify-content-between">
              <div class="fw-semibold">${escapeHtml(t1)} vs ${escapeHtml(t2)}</div>
              <div class="d-flex gap-2 flex-wrap">
                <span class="badge text-bg-${badge}">${escapeHtml(m.status)}</span>
                <span class="badge text-bg-${catBadge}">${escapeHtml(m.category)}</span>
                <span class="badge text-bg-${genderBadge}">${escapeHtml(m.gender)}</span>
                <span class="badge text-bg-light text-dark border">${escapeHtml(m.format || 'other')}</span>
              </div>
            </div>
            <div class="small text-body-secondary mt-1">
              ${escapeHtml(m.seriesName || '')}
              ${m.venue ? ` • ${escapeHtml(m.venue)}` : ''}
              ${m.date ? ` • ${escapeHtml(m.date)}` : ''}
            </div>
            ${m.resultText ? `<div class="mt-2">${escapeHtml(m.resultText)}</div>` : ''}
            <div class="small text-body-secondary mt-2">Source: ${escapeHtml(m.source)}</div>
          </div>
        </div>
      `;
    })
    .join('');
}

function applyFilters() {
  const category = el.categoryFilter.value;
  const gender = el.genderFilter.value;
  const format = el.formatFilter.value;
  const status = el.statusFilter.value;
  const q = el.searchInput.value.trim().toLowerCase();

  const filtered = allMatches.filter((m) => {
    if (category !== 'all' && m.category !== category) return false;
    if (gender !== 'all' && m.gender !== gender) return false;
    if (format !== 'all') {
      if (format === 'other') {
        if (['test', 'odi', 't20', 't10'].includes(m.format)) return false;
      } else if (m.format !== format) return false;
    }
    if (status !== 'all' && m.status !== status) return false;

    if (q) {
      const hay = `${m.name} ${m.seriesName} ${m.venue} ${m.teams?.[0]?.name} ${m.teams?.[1]?.name}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }

    return true;
  });

  render(filtered);
}

async function load() {
  el.refreshBtn.disabled = true;
  el.refreshBtn.textContent = 'Refreshing…';
  setStatus(el.statusBar, { message: 'Loading matches from both APIs…', show: true });

  try {
    const [recent, live, current] = await Promise.all([
      fetchCricbuzzRecent(),
      fetchCricbuzzLive(),
      fetchCurrentMatches({ maxPages: 2 })
    ]);

    const fromCricbuzz = [...mapCricbuzzToMatches(recent), ...mapCricbuzzToMatches(live)];
    const fromCricapi = current.map(normalizeMatchFromCricApi);

    allMatches = mergeAndDedupeMatches([...fromCricbuzz, ...fromCricapi]);
    setStatus(el.statusBar, { type: 'success', message: `Loaded ${allMatches.length} matches (deduped).`, show: true });
    applyFilters();
  } catch (e) {
    console.error(e);
    setStatus(el.statusBar, { type: 'danger', message: e?.message || 'Failed to load matches', show: true });
    el.matchesList.innerHTML = '<div class="text-danger">Failed to load matches. Check API keys in app/config.js</div>';
  } finally {
    el.refreshBtn.disabled = false;
    el.refreshBtn.textContent = 'Refresh';
  }
}

function escapeHtml(s) {
  return String(s ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

for (const control of [el.categoryFilter, el.genderFilter, el.formatFilter, el.statusFilter, el.searchInput]) {
  control.addEventListener('input', applyFilters);
  control.addEventListener('change', applyFilters);
}

el.refreshBtn.addEventListener('click', load);

load();
