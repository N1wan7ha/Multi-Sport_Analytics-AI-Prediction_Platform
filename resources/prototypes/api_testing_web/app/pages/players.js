import { searchPlayers } from '../api/cricapi.js';
import { qs, setStatus } from '../ui/dom.js';

const el = {
  searchBtn: qs('searchBtn'),
  playerSearch: qs('playerSearch'),
  playersList: qs('playersList'),
  statusBar: document.getElementById('statusBar')
};

function render(players) {
  if (!players.length) {
    el.playersList.innerHTML = '<div class="text-body-secondary">No players found.</div>';
    return;
  }

  el.playersList.innerHTML = players
    .slice(0, 50)
    .map((p) => {
      const id = p?.id || '';
      const name = p?.name || '';
      const country = p?.country || '';

      return `
        <a class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" href="player.html?id=${encodeURIComponent(id)}">
          <div>
            <div class="fw-semibold">${escapeHtml(name)}</div>
            <div class="small text-body-secondary">${escapeHtml(country)}</div>
          </div>
          <span class="badge text-bg-light text-dark border">View</span>
        </a>
      `;
    })
    .join('');
}

async function doSearch() {
  const q = el.playerSearch.value.trim();
  if (!q) {
    setStatus(el.statusBar, { type: 'warning', message: 'Enter a search term.', show: true });
    return;
  }

  el.searchBtn.disabled = true;
  el.searchBtn.textContent = 'Searching…';
  setStatus(el.statusBar, { message: 'Searching players…', show: true });

  try {
    const rows = await searchPlayers({ search: q, maxPages: 2 });
    setStatus(el.statusBar, { type: 'success', message: `Found ${rows.length} players (showing up to 50).`, show: true });
    render(rows);
  } catch (e) {
    console.error(e);
    setStatus(el.statusBar, { type: 'danger', message: e?.message || 'Failed to search players', show: true });
    el.playersList.innerHTML = '<div class="text-danger">Failed to search players. Check API key in app/config.js</div>';
  } finally {
    el.searchBtn.disabled = false;
    el.searchBtn.textContent = 'Search';
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

el.searchBtn.addEventListener('click', doSearch);
el.playerSearch.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') doSearch();
});
