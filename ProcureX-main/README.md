# ProcureX

Smart Procurement & Vendor Management System for a DBMS course project.

## Architecture

```text
React + Vite frontend
        ↓ HTTP API
Flask + Python backend
        ↓ SQL (psycopg2)
PostgreSQL database
```

CRUD operations are executed as SQL in the Flask backend against PostgreSQL.

## Project structure

```text
ProcureX-main/
├─ src/                     React frontend
├─ backend/
│  ├─ app.py                Flask API + SQL CRUD queries
│  ├─ db.py                 PostgreSQL connection
│  ├─ schema.sql            18-table PostgreSQL schema
│  ├─ seed.sql              sample TechNova data
│  ├─ vendor_ranking.sql    50/20/30 vendor ranking query
│  ├─ requirements.txt
│  └─ .env.example
├─ .env.example             frontend API URL example
└─ package.json
```

## 1. Create the PostgreSQL database

Create a database named `procurex` using pgAdmin or psql.

Example in psql:

```sql
CREATE DATABASE procurex;
```

Then run `backend/schema.sql`, followed by `backend/seed.sql`, inside the `procurex` database.

## 2. Start the Flask backend

Open a terminal in `backend`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and set your PostgreSQL password:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=procurex
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
FLASK_PORT=5000
```

Start Flask:

```powershell
python app.py
```

Backend runs at `http://127.0.0.1:5000`.

Test it in your browser:

```text
http://127.0.0.1:5000/api/health
```

## 3. Start the React frontend

Open a second terminal in the project root:

```powershell
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Delete-button flow for viva

Frontend (`src/App.jsx`):

```js
await fetch(`${API_URL}/crud/${table}/${idColumn}/${idValue}`, {
  method: 'DELETE',
});
```

Flask backend (`backend/app.py`):

```python
query = sql.SQL("DELETE FROM {table} WHERE {id_column} = %s RETURNING *").format(
    table=sql.Identifier(table),
    id_column=sql.Identifier(id_column),
)
cur.execute(query, (id_value,))
```

For PR 3, this is equivalent to:

```sql
DELETE FROM purchase_request WHERE pr_id = 3;
```

## Vendor scoring

The project keeps the same formula:

- 50% price
- 20% delivery
- 30% vendor rating

The SQL version is in `backend/vendor_ranking.sql` and is also available through:

```text
GET /api/vendor-ranking/1
```
