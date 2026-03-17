# Text-to-SQL Evaluation Platform

A comprehensive automated testing platform for evaluating Text-to-SQL AI agents.

## Project Overview

This platform tests AI agents by:

1. Sending natural language questions to the agent
2. Getting SQL queries from the agent
3. Running both golden (expected) SQL and agent SQL in a sandbox
4. Comparing results
5. Using LLM to diagnose failures (optional)

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Vue 3 + Vite + TypeScript + Element Plus
- **Database**: SQLite (file-based)

## Project Structure

```
file/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── config.py       # Settings
│   │   ├── database.py     # DB session
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic models
│   │   ├── routers/       # API endpoints
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utilities (SQL security)
│   └── requirements.txt
│
└── frontend/               # Vue 3 application
    ├── src/
    │   ├── views/         # Page components
    │   ├── api/           # API client
    │   ├── types/         # TypeScript types
    │   └── router/        # Vue Router
    └── package.json
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+

### One Command Start (Recommended)

```bash
python start.py
```

Optional:

```bash
python start.py --skip-install
```

### 1. Start Backend

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:

- API: <http://localhost:8000>
- Docs: <http://localhost:8000/docs>

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: <http://localhost:5173>

## Usage Flow

### Step 1: Create Environment

Go to "Environment" page → Create a new environment with:

- Name (e.g., "E-commerce DB")
- DDL content (CREATE TABLE statements)

### Step 2: Create Test Cases

Go to "Test Cases" page → Add test cases:

- Question (natural language)
- Golden SQL (expected answer)
- Link to an environment

### Step 3: Configure Agent

Go to "Agents" page → Add your Text-to-SQL agent:

- API endpoint (where to send requests)
- Auth token (if needed)
- Timeout settings

### Step 4: Run Evaluation

Go to "Tasks" page → Create a task:

- Select agent
- Select environment
- Optionally select specific test cases
- Click "Start" to run

### Enable Judge LLM (AI Diagnosis)

If you want failed cases to include AI diagnosis, configure backend once:

1. Copy `backend/.env.example` to `backend/.env`
2. Set:
   - `JUDGE_LLM_ENDPOINT` (your OpenAI-compatible chat completions endpoint)
   - `JUDGE_LLM_API_KEY` (your API key)
   - `JUDGE_LLM_DEFAULT_MODEL` (optional, e.g. `gpt-4o-mini`)
3. Restart backend service

After that:
- In "Tasks" page, "Judge LLM" can be left empty to use backend default model
- Or enter a model name to override for a specific task
- You can also open "Tasks" page and use "裁判模型配置" to:
  - Save endpoint / API key / default model directly in UI
  - Click "测试连通" to verify provider integration before running evaluations

### Step 5: View Results

- See pass/fail status
- View AI diagnosis for failures
- Check statistics on Dashboard

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | /api/schema-envs | Environment CRUD |
| GET/POST | /api/test-cases | Test case CRUD |
| GET/POST | /api/agents | Agent CRUD |
| GET/POST | /api/tasks | Task CRUD |
| POST | /api/tasks/{id}/start | Start evaluation |
| GET | /api/tasks/{id}/progress | Get progress |
| GET | /api/results | Get results |
| GET | /api/dashboard/stats | Dashboard stats |

## Key Features

1. **Sandbox Execution**: SQL runs in isolated in-memory database
2. **Security**: Blocks dangerous operations (DROP, DELETE, UPDATE)
3. **LIMIT Enforcement**: All queries limited to 100 rows
4. **Timeout Protection**: 5 second query timeout
5. **LLM Diagnosis**: Optional AI analysis of failures
6. **Result Comparison**: Unordered comparison of result sets

## Configuration

Edit `backend/app/config.py` to change:

```python
database_url: str = "sqlite+aiosqlite:///./text2sql.db"
query_timeout_seconds: int = 5
max_result_rows: int = 100
rate_limit_qps: int = 10
judge_llm_endpoint: Optional[str] = None  # For AI diagnosis
judge_llm_api_key: Optional[str] = None
```

## Troubleshooting

### Backend won't start

- Check Python version: `python --version` (need 3.9+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is not in use

### Frontend won't start

- Check Node.js: `node --version` (need 18+)
- Reinstall: `rm -rf node_modules && npm install`

### API calls fail

- Check backend is running on port 8000
- Check CORS settings in `app/main.py`
- Check browser console for errors

### Database issues

- Delete `text2sql.db` file to reset
- Restart backend to recreate

## For Development

### Add new model

1. Create model in `app/models/`
2. Create schema in `app/schemas/`
3. Create router in `app/routers/`
4. Register in `app/main.py`

### Add new frontend page

1. Create Vue component in `src/views/`
2. Add route in `src/router/index.ts`
3. Add link in `src/App.vue`

## License

MIT
