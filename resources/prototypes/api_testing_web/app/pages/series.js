import { fetchSeriesInfo, fetchSeriesList } from '../api/cricapi.js';
import { inferCategory, inferGender } from '../domain/normalize.js';
import { qs, setStatus } from '../ui/dom.js';

const el = {
  refreshBtn: qs('refreshBtn'),
  seriesList: qs('seriesList'),
  statusBar: document.getElementById('statusBar'),
  seriesSearch: qs('seriesSearch'),
  categoryFilter: qs('categoryFilter'),
  genderFilter: qs('genderFilter'),
  seriesMatches: qs('seriesMatches')
};

let allSeries = [];

function seriesCategory(seriesName) {
  return inferCategory({ seriesName, matchName: seriesName, categoryHint: '' });
}

function seriesGender(seriesName) {
  return inferGender(seriesName);
}

function render() {
  const category = el.categoryFilter.value;
  const gender = el.genderFilter.value;
  const q = el.seriesSearch.value.trim().toLowerCase();

  const filtered = allSeries.filter((s) => {
    const name = s?.name || '';
    const cat = seriesCategory(name);
    const gen = seriesGender(name);

    if (category !== 'all' && cat !== category) return false;
    if (gender !== 'all' && gen !== gender) return false;
    if (q && !name.toLowerCase().includes(q)) return false;
    return true;
  });

  if (!filtered.length) {
    el.seriesList.innerHTML = '<div class="text-body-secondary">No series found.</div>';
    return;
  }

  el.seriesList.innerHTML = filtered.map((s) => {
    const name = s?.name || '';
    const cat = seriesCategory(name);
    const gen = seriesGender(name);
    const fmt = `Test: ${s?.test ?? 0} • ODI: ${s?.odi ?? 0} • T20: ${s?.t20 ?? 0}`;

    return `
      <div class="card">
        <div class="card-body">
          <div class="d-flex flex-wrap gap-2 align-items-center justify-content-between">
            <div>
              <div class="fw-semibold">${escapeHtml(name)}</div>
              <div class="small text-body-secondary">${escapeHtml(fmt)}</div>
            </div>
            <div class="d-flex flex-wrap gap-2 align-items-center">
              <span class="badge text-bg-${cat === 'franchise' ? 'warning' : 'info'}">${escapeHtml(cat)}</span>
              <span class="badge text-bg-${gen === 'women' ? 'primary' : 'dark'}">${escapeHtml(gen)}</span>
              <button class="btn btn-sm btn-outline-primary" data-series-id="${escapeHtml(s?.id || '')}">Load matches</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function load() {
  el.refreshBtn.disabled = true;
  el.refreshBtn.textContent = 'Refreshing…';
  setStatus(el.statusBar, { message: 'Loading series from CricAPI…', show: true });

  try {
    // Load first ~100 rows by default.
    allSeries = await fetchSeriesList({ search: '', maxPages: 4 });
    setStatus(el.statusBar, { type: 'success', message: `Loaded ${allSeries.length} series.`, show: true });
    render();
  } catch (e) {
    console.error(e);
    setStatus(el.statusBar, { type: 'danger', message: e?.message || 'Failed to load series', show: true });
    el.seriesList.innerHTML = '<div class="text-danger">Failed to load series. Check API key in app/config.js</div>';
  } finally {
    el.refreshBtn.disabled = false;
    el.refreshBtn.textContent = 'Refresh';
  }
}

async function loadSeriesMatches(seriesId) {
  if (!seriesId) return;

  setStatus(el.statusBar, { message: 'Loading series_info (this can be heavy)…', show: true });
  el.seriesMatches.innerHTML = '';

  try {
    const data = await fetchSeriesInfo(seriesId);
    const matches = Array.isArray(data?.matchList) ? data.matchList : [];

    if (!matches.length) {
      el.seriesMatches.innerHTML = '<div class="text-body-secondary">No match list available for this series.</div>';
      return;
    }

    // CricketData series_info match objects vary; render defensively.
    el.seriesMatches.innerHTML = matches.map((m) => {
      const name = m?.name || m?.matchName || '';
      const fmt = String(m?.matchType || m?.matchFormat || '').toLowerCase() || 'other';
      const date = m?.date || (m?.dateTimeGMT ? String(m.dateTimeGMT).slice(0, 10) : '');
      const venue = m?.venue || '';
      const status = m?.status || '';

      return `
        <div class="card">
          <div class="card-body">
            <div class="d-flex flex-wrap gap-2 align-items-center justify-content-between">
              <div class="fw-semibold">${escapeHtml(name)}</div>
              <span class="badge text-bg-light text-dark border">${escapeHtml(fmt)}</span>
            </div>
            <div class="small text-body-secondary mt-1">
              ${date ? escapeHtml(date) : ''}
              ${venue ? ` • ${escapeHtml(venue)}` : ''}
            </div>
            ${status ? `<div class="mt-2">${escapeHtml(status)}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');

    setStatus(el.statusBar, { type: 'success', message: `Loaded ${matches.length} matches for the selected series.`, show: true });
  } catch (e) {
    console.error(e);
    setStatus(el.statusBar, { type: 'danger', message: e?.message || 'Failed to load series_info', show: true });
    el.seriesMatches.innerHTML = '<div class="text-danger">Failed to load series matches.</div>';
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

el.refreshBtn.addEventListener('click', load);
for (const control of [el.seriesSearch, el.categoryFilter, el.genderFilter]) {
  control.addEventListener('input', render);
  control.addEventListener('change', render);
}

el.seriesList.addEventListener('click', (e) => {
  const btn = e.target?.closest('button[data-series-id]');
  if (!btn) return;
  loadSeriesMatches(btn.getAttribute('data-series-id'));
});

load();
