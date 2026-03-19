import { inferCategory, inferGender } from './normalize.js';

function teamKey(teamName) {
  return String(teamName || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function fingerprint(match) {
  const t1 = teamKey(match?.teams?.[0]?.name);
  const t2 = teamKey(match?.teams?.[1]?.name);
  const teams = [t1, t2].filter(Boolean).sort().join('|');
  const date = String(match?.date || '').slice(0, 10);
  const fmt = String(match?.format || 'other');
  return `${teams}__${date}__${fmt}`;
}

function mergeTwo(a, b) {
  const merged = { ...a };
  for (const key of ['name', 'seriesName', 'venue', 'date', 'format', 'status', 'resultText']) {
    if (!merged[key] && b[key]) merged[key] = b[key];
  }

  // Prefer live > complete > upcoming
  const order = { live: 3, complete: 2, upcoming: 1 };
  if ((order[b.status] || 0) > (order[merged.status] || 0)) merged.status = b.status;

  merged.sources = Array.from(new Set([...(a.sources || [a.source]), ...(b.sources || [b.source])].filter(Boolean)));
  merged.source = merged.sources.join('+');
  return merged;
}

export function mergeAndDedupeMatches(matches) {
  const map = new Map();
  for (const m of matches) {
    const key = fingerprint(m);
    const existing = map.get(key);
    if (!existing) {
      map.set(key, { ...m, sources: [m.source].filter(Boolean) });
    } else {
      map.set(key, mergeTwo(existing, m));
    }
  }

  const out = Array.from(map.values());
  for (const m of out) {
    m.gender = inferGender(`${m.seriesName} ${m.name}`);
    m.category = inferCategory({ categoryHint: m.categoryHint, seriesName: m.seriesName, matchName: m.name });
  }
  return out;
}
