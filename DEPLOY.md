# Deployment Guide

## Option A — Railway (recommended, fastest)

1. Create account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub (or upload the `backend` folder)
3. Railway will detect the Dockerfile / Python app
4. Set the start command if needed:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Once deployed, copy the public URL (e.g. `https://kalshi-parlays-production.up.railway.app`)

6. Update the frontend:
   - Open `frontend/index.html`
   - Change:
     ```js
     const API_BASE = 'http://localhost:8000';
     ```
     to your Railway URL:
     ```js
     const API_BASE = 'https://your-app.up.railway.app';
     ```

7. Deploy the frontend:
   - Drag the `frontend` folder to [app.netlify.com/drop](https://app.netlify.com/drop)
   - Or connect the repo to Vercel / Netlify

---

## Option B — Render

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your repo (or upload)
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. After deploy, update `API_BASE` in the frontend the same way as above

---

## Option C — Frontend only (Netlify / Vercel)

The frontend is static. After the API is live:

**Netlify Drop** (easiest):
- Go to https://app.netlify.com/drop
- Drag the entire `frontend` folder

**Vercel**:
```bash
cd frontend
npx vercel
```

---

## After deployment — Install as app on your phone

### iPhone
1. Open the frontend URL in Safari
2. Tap the Share button
3. Tap **Add to Home Screen**
4. It will appear as a full-screen app

### Android
1. Open the frontend URL in Chrome
2. Tap the menu (⋮) → **Install app** / **Add to Home Screen**

---

## Local testing of PWA

```bash
# Terminal 1 – API
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 – Frontend (must be served over http, not file://)
cd frontend
python -m http.server 3000
```

Then open http://localhost:3000 and use Chrome DevTools → Application → Service Workers to verify.
