# Daniel_Portfolio
My personal developer portfolio showcasing my projects, technical skills, experience, and work in Python, Django, SQL, APIs, and web development.

## Local Django and PostgreSQL setup

Install the Python dependencies and create a local environment file:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` in `.env` with private values. Keep `.env` out of version control.

Create the PostgreSQL role and database using SQL Shell (`psql`) or another PostgreSQL administration client, replacing the example password:

```sql
CREATE ROLE portfolio_user WITH LOGIN CREATEDB PASSWORD 'replace-with-your-database-password';
CREATE DATABASE portfolio OWNER portfolio_user;
```

`CREATEDB` lets Django create its temporary database when running the test suite. For production, use a dedicated least-privilege database role without `CREATEDB`. The default `.env.example` connection uses `localhost:5432`, database `portfolio`, and role `portfolio_user`. Update those environment values if your PostgreSQL server uses different settings.

Apply the migrations, create an admin account, and start Django:

```powershell
.\venv\Scripts\python.exe manage.py makemigrations
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

Run the portfolio and contact form tests with:

```powershell
.\venv\Scripts\python.exe manage.py test website
```

The contact form stores validated submissions in the `website_contact` table. View them at `/admin/` after signing in. The migration renames the existing `ContactMessage` model and database table without dropping its records. The existing `db.sqlite3` file is not deleted or modified, but records in SQLite are not copied into PostgreSQL automatically; back up and migrate any existing site content separately before switching a populated deployment to PostgreSQL.

## Real-Time Gemini AI Voice Assistant & RAG Setup

The portfolio includes an interactive floating AI voice assistant powered by Google Gemini and PostgreSQL RAG (Retrieval-Augmented Generation), grounded strictly in Daniel John Britto's verified resume.

### 1. Environment Configuration

Add the Google Gemini API configuration to your private `.env` file (never commit `.env` to Git):

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-flash-latest
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

### 2. Loading & Embedding Resume Knowledge

Seed and generate 3072-dimensional vector embeddings for Daniel's verified resume chunks into PostgreSQL:

```powershell
.\venv\Scripts\python.exe manage.py load_resume_knowledge
```

To force re-embedding existing chunks at any time, run:

```powershell
.\venv\Scripts\python.exe manage.py load_resume_knowledge --force
```

### 3. Voice Features & Browser Support

- **Speech-to-Text (Voice Input)**: Uses browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`). Supported in Chrome, Edge, and Safari.
- **Text-to-Speech (Spoken Responses)**: Uses browser `speechSynthesis`. The assistant speaks answers aloud automatically whenever voice input is used.
- **Voice Modes**:
  - **Push-to-Talk**: Tap the microphone button to ask a question by voice.
  - **Continuous Conversation**: Click the sync/loop button in the header to allow ongoing hands-free conversation (auto-listens after finishing each spoken answer).
- **Controls**: Includes Interrupt/Stop, Replay audio for individual responses, and Mute/Unmute toggle.

### 4. Running Tests

Run all unit tests covering both the website and the AI voice assistant:

```powershell
.\venv\Scripts\python.exe manage.py test
```

