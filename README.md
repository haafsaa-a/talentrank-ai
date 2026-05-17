# TalentRank AI

TalentRank AI is a recruiter-facing platform that automatically collects candidate profiles via Google Form, enriches them using LinkedIn OAuth + GitHub API + portfolio scraping, and ranks candidates using AI.

## Setup Instructions

### 1. LinkedIn Developer App
1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/).
2. Create an App.
3. Add the "Sign In with LinkedIn using OpenID Connect" product to your app.
4. Get your `Client ID` and `Client Secret`.
5. Add `http://localhost:8000/auth/linkedin/callback` as an authorized redirect URL.

### 2. Google Sheets API
1. Create a project in Google Cloud Console.
2. Enable the Google Sheets API.
3. Create a Service Account, download the JSON credentials, and save it as `backend/service_account.json`.
4. Share your target Google Sheet with the Service Account email.

### 3. Environment Variables
1. Copy `backend/.env.example` to `backend/.env` (or just edit the generated `.env`).
2. Fill in the required API keys (OpenAI, GitHub, LinkedIn, SMTP).
3. Generate a 32-byte base64 Fernet key for `ENCRYPTION_KEY` (e.g., using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

## Running Locally

### Option A: Docker Compose (Recommended)
```bash
docker-compose up --build
```
- Backend runs on `http://localhost:8000`
- API Endpoints on `http://localhost:8000/docs`
- Frontend runs on `http://localhost:5173`

### Option B: Manual
**Backend:**
```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate, on Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
``` 

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Testing the Flow
1. Access the dashboard at `http://localhost:5173`.
2. Add a new candidate or use the mock endpoint `/api/mock/candidates`.
3. To trigger the LinkedIn flow, navigate to `http://localhost:8000/auth/linkedin/start?email=candidate@email.com`
