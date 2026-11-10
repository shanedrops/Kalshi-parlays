# Kalshi Daily Parlays

Ranked daily sports combos from Kalshi prediction markets.

- **Core list**: Highest probability first (target 2–4.6× payout)
- **Upside list**: Higher risk options (5–11× payout)
- Live data + 12-minute cache
- Dark mode + PWA (installable on phone)

## Quick Start (Local)

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
python -m http.server 3000
```
Open http://localhost:3000

## Project Structure

```
kalshi-parlay-app/
├── backend/
│   ├── main.py              # FastAPI + caching
│   ├── kalshi_client.py
│   ├── generator.py
│   ├── ranker.py
│   ├── models.py
│   ├── run_daily.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html           # UI (dark mode + PWA)
│   ├── manifest.json
│   ├── sw.js                # Service worker
│   ├── icon-192.png
│   └── icon-512.png
├── DEPLOY.md                # Deployment instructions
├── railway.toml
├── render.yaml
└── README.md
```

## Features

- Ranked by estimated win probability (safest first)
- Separate Higher Upside (5–10x) section
- In-memory cache (12 min TTL) — fast responses after first load
- Force refresh available
- Dark mode (system preference + toggle)
- Installable PWA on iOS and Android

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /combos/today` | Main ranked list (cached) |
| `GET /combos/today?force_refresh=true` | Bypass cache |
| `GET /cache/status` | Cache age & validity |
| `POST /cache/clear` | Clear cache |
| `GET /health` | Health check |

## Deploy

See **DEPLOY.md** for Railway, Render, Netlify, and Vercel instructions.

After deploying the API, update `API_BASE` in `frontend/index.html` to your live API URL, then deploy the frontend.

## Notes

- Uses Kalshi public market data only (no API key needed for reading).
- Combos are suggestions. Actual Kalshi Combo prices are set via RFQ.
- Always verify current prices and rules on Kalshi before trading.
