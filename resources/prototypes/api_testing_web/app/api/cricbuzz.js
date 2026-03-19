import { CRICBUZZ_RAPIDAPI } from '../config.js';

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: {
      'X-RapidAPI-Key': CRICBUZZ_RAPIDAPI.rapidApiKey,
      'X-RapidAPI-Host': CRICBUZZ_RAPIDAPI.rapidApiHost
    }
  });

  if (!res.ok) {
    throw new Error(`Cricbuzz(RapidAPI) error ${res.status}`);
  }
  return await res.json();
}

export async function fetchCricbuzzRecent() {
  return await fetchJson(`${CRICBUZZ_RAPIDAPI.baseUrl}/matches/v1/recent`);
}

export async function fetchCricbuzzLive() {
  return await fetchJson(`${CRICBUZZ_RAPIDAPI.baseUrl}/matches/v1/live`);
}

export function mapCricbuzzToMatches(apiResponse) {
  const mapped = [];
  const typeMatches = apiResponse?.typeMatches;
  if (!Array.isArray(typeMatches)) return mapped;

  for (const typeMatch of typeMatches) {
    const categoryHint = (typeMatch?.matchType || '').toLowerCase(); // International/League/Domestic

    const seriesMatches = typeMatch?.seriesMatches;
    if (!Array.isArray(seriesMatches)) continue;

    for (const seriesMatch of seriesMatches) {
      const wrapper = seriesMatch?.seriesAdWrapper;
      const seriesName = wrapper?.seriesName || seriesMatch?.seriesName || '';

      const matches = Array.isArray(seriesMatch?.matches)
        ? seriesMatch.matches
        : Array.isArray(wrapper?.matches)
          ? wrapper.matches
          : null;

      if (!matches) continue;

      for (const match of matches) {
        const info = match?.matchInfo;
        if (!info) continue;

        const startDateMs = Number(info.startDate);
        const dateISO = Number.isFinite(startDateMs)
          ? new Date(startDateMs).toISOString().slice(0, 10)
          : (info.startDate || '');

        mapped.push({
          source: 'cricbuzz',
          id: String(info.matchId ?? ''),
          name: `${info.team1?.teamName ?? 'T1'} vs ${info.team2?.teamName ?? 'T2'}${info.matchDesc ? `, ${info.matchDesc}` : ''}`,
          seriesName,
          teams: [
            { name: info.team1?.teamName ?? 'Unknown', code: info.team1?.teamSName ?? '' },
            { name: info.team2?.teamName ?? 'Unknown', code: info.team2?.teamSName ?? '' }
          ],
          format: normalizeFormat(info.matchFormat),
          date: dateISO,
          venue: info.venueInfo ? `${info.venueInfo.ground}, ${info.venueInfo.city}` : (info.venue || ''),
          status: normalizeStatus(info.state, info.status),
          resultText: info.status || '',
          categoryHint
        });
      }
    }
  }

  return mapped;
}

function normalizeFormat(fmt) {
  const v = String(fmt || '').toLowerCase();
  if (v === 'test') return 'test';
  if (v === 'odi') return 'odi';
  if (v === 't20') return 't20';
  if (v === 't10') return 't10';
  if (v === 't20i') return 't20';
  return v || 'other';
}

function normalizeStatus(state, statusText) {
  const s = String(state || '').toLowerCase();
  if (s.includes('progress') || s === 'live' || s === 'inprogress') return 'live';
  if (s.includes('complete') || s === 'result') return 'complete';
  if (s.includes('preview') || s.includes('upcoming') || s.includes('toss')) return 'upcoming';

  const t = String(statusText || '').toLowerCase();
  if (t.includes('won') || t.includes('draw') || t.includes('abandoned') || t.includes('no result')) return 'complete';
  return 'upcoming';
}
