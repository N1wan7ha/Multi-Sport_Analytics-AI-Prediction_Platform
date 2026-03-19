import { fetchPlayerInfo } from '../api/cricapi.js';
import { getParam, qs, setStatus } from '../ui/dom.js';

const el = {
  playerName: qs('playerName'),
  playerMeta: qs('playerMeta'),
  statusBar: document.getElementById('statusBar'),
  playerCard: qs('playerCard'),
  country: qs('country'),
  role: qs('role'),
  battingStyle: qs('battingStyle'),
  bowlingStyle: qs('bowlingStyle'),
  dob: qs('dob'),
  placeOfBirth: qs('placeOfBirth')
};

function setText(node, value) {
  node.textContent = value ? String(value) : '—';
}

async function load() {
  const id = getParam('id');
  if (!id) {
    setStatus(el.statusBar, { type: 'danger', message: 'Missing player id in URL.', show: true });
    return;
  }

  setStatus(el.statusBar, { message: 'Loading player info…', show: true });

  try {
    const p = await fetchPlayerInfo(id);
    if (!p) {
      setStatus(el.statusBar, { type: 'warning', message: 'Player not found.', show: true });
      return;
    }

    el.playerName.textContent = p?.name || 'Player';
    el.playerMeta.textContent = p?.country ? `Country: ${p.country}` : '';

    setText(el.country, p?.country);
    setText(el.role, p?.role);
    setText(el.battingStyle, p?.battingStyle);
    setText(el.bowlingStyle, p?.bowlingStyle);
    setText(el.dob, p?.dateOfBirth);
    setText(el.placeOfBirth, p?.placeOfBirth);

    el.playerCard.classList.remove('d-none');
    setStatus(el.statusBar, { type: 'success', message: 'Loaded.', show: true });
  } catch (e) {
    console.error(e);
    setStatus(el.statusBar, { type: 'danger', message: e?.message || 'Failed to load player info', show: true });
  }
}

load();
