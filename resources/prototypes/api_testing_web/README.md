# api_testing_web

A small static cricket dashboard (no backend) using:
- Cricbuzz data via RapidAPI
- CricAPI / CricketData (`api.cricapi.com`)

## Structure

- `index.html` – Home
- `pages/` – App pages
  - `pages/matches.html` – Matches (International vs Franchise, Men vs Women, formats)
  - `pages/series.html` – Series list + optional `series_info` matches
  - `pages/players.html` – Player search
  - `pages/player.html` – Player detail

- `app/` – JS modules
  - `app/config.js` – API keys + base URLs
  - `app/api/` – API clients
  - `app/domain/` – normalize + merge/dedupe logic
  - `app/pages/` – page controllers
  - `app/ui/` – small DOM helpers

- `assets/css/styles.css` – tiny CSS tweaks on top of Bootstrap
- `assets/examples/` – sample JSON payloads

## Setup

1) Set keys in `app/config.js`
- `CRICAPI.apiKey` – from https://cricketdata.org/
- `CRICBUZZ_RAPIDAPI.rapidApiKey` – from RapidAPI

2) Run a static server

```powershell
cd "c:\Users\situw\OneDrive\Desktop\Dev\prediction_analytics-Platform\api_testing_web"
python -m http.server 5500
```

Open:
- http://localhost:5500/index.html
