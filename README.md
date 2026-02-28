# Inspection Order Manager (Local Airtable-Style)

## 1) Architecture Overview
- **Backend**: FastAPI + SQLAlchemy 2 + SQLite. Provides CSV import/upsert, saved views, custom fields, activity log, geocoding cache, route optimization, export CSV.
- **Database**: SQLite (`inspection.db`) with tables: `orders`, `custom_fields_definitions`, `order_custom_fields`, `saved_views`, `activity_log`, `geocode_cache`, `app_settings`.
- **Frontend**: React + TypeScript + Vite + MUI + React Query + Leaflet. Table-first workflow with saved view selection, map-first rendering based on current view results, and one-click completion.
- **Routing/Geocode**: Nominatim geocoding with SQLite cache, OSRM trip optimization endpoint.

## 2) Folder/File Tree
```text
.
├── backend
│   ├── alembic
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions
│   │       └── 0001_init.py
│   ├── alembic.ini
│   ├── app
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── services.py
│   ├── requirements.txt
│   └── tests
│       └── test_app.py
├── frontend
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src
│       └── main.tsx
├── sample_inspections.csv
└── README.md
```

## 3) Windows Setup Guide
### Backend
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```
API will run at `http://127.0.0.1:8000`.

### Frontend
```powershell
cd frontend
npm install
npm run dev
```
UI will run at `http://127.0.0.1:5173`.

## 4) Usage Highlights
- Import CSV: `POST /orders/import_csv` (uses `Assignment #` upsert semantics and row-level error report).
- Saved view controls table + map scope (`GET /orders?view_id=...`).
- One-click complete: `POST /orders/{id}/complete`.
- Bulk geocode current view: `POST /geocode/bulk?view_id=...`.
- Route optimize from configured start: `POST /route/optimize?view_id=...`.
- Export current view CSV: `GET /orders/export_csv?view_id=...`.

## 5) Testing
```powershell
cd backend
pytest
```
Covers import upsert, saved-view filtering, complete action, and export CSV.
