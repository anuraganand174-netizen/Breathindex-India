# AQI India — Analyzer & Health Impact

Portfolio-ready air quality dashboard with Flask API, ML forecasts (Random Forest / XGBoost), health impact guidance, and cloud deployment (Render + GitHub Pages).

## Stack

| Layer | Technology |
|-------|------------|
| API | Flask 3 + Flask-CORS + Gunicorn |
| DB | SQLite (demo) or MySQL (production) |
| ML | scikit-learn, XGBoost, joblib |
| Frontend | HTML/CSS/JS → GitHub Pages |
| Hosting | Render (API), Railway (optional) |

## Project structure

```
AQI Project/
├── api/flask_api.py          # Flask app & routes
├── backend/
│   ├── config.py             # Env-based configuration
│   ├── db.py                 # SQLAlchemy engine
│   └── services/             # AQI, health, ML logic
├── database/
│   ├── schema.sql            # SQLite schema
│   └── schema_mysql.sql      # MySQL schema
├── frontend/                 # Static dashboard (GitHub Pages)
├── models/artifacts/         # Trained .joblib models
├── scripts/                  # DB init, seed, train
├── data/aqi_local.db         # Seeded SQLite (optional commit)
├── requirements.txt
├── runtime.txt               # Python 3.11.9 for Render
├── Procfile
├── wsgi.py                   # Gunicorn entrypoint
├── render.yaml               # Render Blueprint
├── railway.toml              # Railway config
├── .env.example
└── DEPLOY.md                 # Step-by-step deploy guide
```

## Local setup

```powershell
cd "d:\AQI Project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Initialize (if starting fresh):

```powershell
python scripts\init_db.py
python scripts\load_states_cities.py
python scripts\generate_and_load_mock_history.py --days 90
python scripts\train_models.py --source db --models random_forest,xgboost --horizons 1,7,30
```

Run API:

```powershell
python -m api.flask_api
# or
gunicorn wsgi:app --bind 127.0.0.1:5055
```

Open http://127.0.0.1:5055/ for the dashboard.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness + DB ping |
| GET | `/api/states` | List states |
| GET | `/api/cities?state_id=` | Cities by state |
| GET | `/api/aqi/latest?city_id=` | Latest reading |
| GET | `/api/aqi/history?city_id=&days=` | Time series |
| GET | `/api/health-impact?aqi=` | Health band |
| GET | `/api/predict?city_id=&model=&horizon=` | ML forecast |
| GET | `/api/stats/summary` | DB counts |

## Environment variables

See [.env.example](.env.example). Key variables:

- `USE_SQLITE=1` — use file DB under `data/`
- `DATABASE_URL` — MySQL URL for managed DB
- `CORS_ORIGINS` — allow GitHub Pages origin
- `SECRET_KEY` — Flask secret (required in production)

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for Render, GitHub Pages, Railway, git commands, and troubleshooting.

## License

MIT — portfolio / educational use.
