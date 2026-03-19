import { CRICAPI } from '../config.js';

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`CricAPI error ${res.status}`);
  }
  const data = await res.json();
  if (data?.status && data.status !== 'success') {
    throw new Error(`CricAPI failure: ${data.status}`);
  }
  return data;
}

export async function fetchCricApiPaged(path, params = {}) {
  const pageSize = 25;
  let offset = Number(params.offset ?? 0);
  const all = [];

  while (true) {
    const qs = new URLSearchParams({
      apikey: CRICAPI.apiKey,
      offset: String(offset),
      ...Object.fromEntries(Object.entries(params).filter(([k]) => k !== 'offset'))
    });

    const url = `${CRICAPI.baseUrl}${path}?${qs.toString()}`;
    const payload = await fetchJson(url);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    all.push(...rows);

    const totalRows = payload?.info?.totalRows;
    if (typeof totalRows === 'number') {
      if (offset + pageSize >= totalRows) break;
    }

    if (rows.length < pageSize) break;
    offset += pageSize;
  }

  return all;
}

export async function fetchSeriesList({ search = '', maxPages = 4 } = {}) {
  const params = {};
  if (search) params.search = search;

  // Limit pages to avoid huge client-side loads.
  const pageSize = 25;
  const all = [];
  for (let page = 0; page < maxPages; page++) {
    const offset = page * pageSize;
    const qs = new URLSearchParams({ apikey: CRICAPI.apiKey, offset: String(offset), ...params });
    const url = `${CRICAPI.baseUrl}/series?${qs.toString()}`;
    const payload = await fetchJson(url);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    all.push(...rows);

    const totalRows = payload?.info?.totalRows;
    if (typeof totalRows === 'number' && offset + pageSize >= totalRows) break;
    if (rows.length < pageSize) break;
  }
  return all;
}

export async function fetchCurrentMatches({ maxPages = 2 } = {}) {
  const pageSize = 25;
  const all = [];
  for (let page = 0; page < maxPages; page++) {
    const offset = page * pageSize;
    const qs = new URLSearchParams({ apikey: CRICAPI.apiKey, offset: String(offset) });
    const url = `${CRICAPI.baseUrl}/currentMatches?${qs.toString()}`;
    const payload = await fetchJson(url);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    all.push(...rows);

    const totalRows = payload?.info?.totalRows;
    if (typeof totalRows === 'number' && offset + pageSize >= totalRows) break;
    if (rows.length < pageSize) break;
  }
  return all;
}

export async function searchPlayers({ search, maxPages = 2 } = {}) {
  const pageSize = 25;
  const all = [];
  for (let page = 0; page < maxPages; page++) {
    const offset = page * pageSize;
    const qs = new URLSearchParams({ apikey: CRICAPI.apiKey, offset: String(offset) });
    if (search) qs.set('search', search);

    const url = `${CRICAPI.baseUrl}/players?${qs.toString()}`;
    const payload = await fetchJson(url);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    all.push(...rows);

    const totalRows = payload?.info?.totalRows;
    if (typeof totalRows === 'number' && offset + pageSize >= totalRows) break;
    if (rows.length < pageSize) break;
  }
  return all;
}

export async function fetchPlayerInfo(playerId) {
  const qs = new URLSearchParams({ apikey: CRICAPI.apiKey, offset: '0', id: playerId });
  const url = `${CRICAPI.baseUrl}/players_info?${qs.toString()}`;
  const payload = await fetchJson(url);
  return payload?.data ?? null;
}

export async function fetchSeriesInfo(seriesId) {
  const qs = new URLSearchParams({ apikey: CRICAPI.apiKey, offset: '0', id: seriesId });
  const url = `${CRICAPI.baseUrl}/series_info?${qs.toString()}`;
  const payload = await fetchJson(url);
  return payload?.data ?? null;
}
