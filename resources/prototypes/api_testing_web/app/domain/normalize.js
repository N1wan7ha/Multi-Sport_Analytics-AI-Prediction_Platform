const FRANCHISE_KEYWORDS = [
  'ipl', 'bbl', 'cpl', 'psl', 'bpl', 'lpl', 'hundred', 'sa20', 'mlc', 'ilt20', 't10', 'super smash', 'big bash', 'caribbean premier', 'pakistan super'
];

export function normalizeFormat(format) {
  const v = String(format || '').toLowerCase();
  if (v === 'test') return 'test';
  if (v === 'odi') return 'odi';
  if (v === 't20') return 't20';
  if (v === 't10') return 't10';
  return v || 'other';
}

export function inferGender(text) {
  const t = String(text || '').toLowerCase();
  if (t.includes('women') || t.includes('womens') || t.includes('women\'s')) return 'women';
  return 'men';
}

export function inferCategory({ categoryHint = '', seriesName = '', matchName = '' } = {}) {
  const hint = String(categoryHint || '').toLowerCase();
  const combined = `${seriesName} ${matchName}`.toLowerCase();

  if (hint.includes('international')) return 'international';
  if (hint.includes('league')) return 'franchise';

  for (const kw of FRANCHISE_KEYWORDS) {
    if (combined.includes(kw)) return 'franchise';
  }

  return 'international';
}

export function normalizeMatchFromCricApi(row) {
  // Based on CricketData list APIs: /matches and /currentMatches
  // Example fields: id, name, matchType, status, venue, date, dateTimeGMT, teams
  const name = row?.name || '';
  const teams = Array.isArray(row?.teams)
    ? row.teams.map((t) => ({ name: t, code: '' }))
    : inferTeamsFromName(name);

  const seriesName = row?.series || row?.seriesName || '';

  return {
    source: 'cricapi',
    id: String(row?.id ?? ''),
    name,
    seriesName,
    teams,
    format: normalizeFormat(row?.matchType),
    date: row?.date || (row?.dateTimeGMT ? String(row.dateTimeGMT).slice(0, 10) : ''),
    venue: row?.venue || '',
    status: normalizeCricApiStatus(row?.status),
    resultText: row?.status || '',
    categoryHint: ''
  };
}

function inferTeamsFromName(name) {
  const parts = String(name || '').split(' vs ');
  if (parts.length === 2) {
    return [{ name: parts[0].trim(), code: '' }, { name: parts[1].split(',')[0].trim(), code: '' }];
  }
  return [{ name: 'Unknown', code: '' }, { name: 'Unknown', code: '' }];
}

function normalizeCricApiStatus(statusText) {
  const t = String(statusText || '').toLowerCase();
  if (!t) return 'upcoming';
  if (t.includes('scheduled') || t.includes('preview')) return 'upcoming';
  if (t.includes('live') || t.includes('inning') || t.includes('day ') || t.includes('stumps')) return 'live';
  if (t.includes('won') || t.includes('draw') || t.includes('abandoned') || t.includes('no result') || t.includes('tie')) return 'complete';
  return 'upcoming';
}
