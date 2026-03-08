# Lynd Clinical — Recruitment Voice Agent

An AI-powered voice agent that automates clinical trial patient outreach. When a physician refers a patient, Lynd places a phone call, verifies identity, explains the study, runs a pre-screening questionnaire, and schedules a follow-up with a study coordinator.

## How It Works

1. **Referral intake** — A provider submits a referral via the REST API (or the demo page)
2. **Outreach queue** — Celery picks up the referral and triggers an outbound Twilio call
3. **Voice conversation** — The agent runs a state-machine-driven call:
   - Greets the patient by name, establishes physician referral context
   - Verifies identity via date of birth (parsed by Claude Haiku)
   - Introduces the study and gauges interest
   - Asks pre-screening questions
   - Offers to schedule a coordinator call
4. **Session saved** — Transcript, state history, and outcomes are persisted to PostgreSQL

## Architecture

```
Browser (Demo Page)
    │
    ▼
FastAPI  ──────►  Celery Worker  ──────►  Twilio (outbound call)
    │                                          │
    │                                          ▼
    │                                    Twilio Media Stream (WebSocket)
    │                                          │
    │                              ┌───────────┼───────────┐
    │                              ▼           ▼           ▼
    │                         Deepgram    Claude Haiku  ElevenLabs
    │                          (STT)    (intent/DOB)    (TTS)
    │                              │           │           │
    │                              └───────────┼───────────┘
    │                                          ▼
    │                                  Conversation State Machine
    │                                          │
    └──────────────────────────────────────────┘
                                               │
                                               ▼
                                          PostgreSQL
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Task Queue | Celery + Redis (Upstash) |
| Database | PostgreSQL + pgvector |
| Telephony | Twilio (Voice, Media Streams, SMS) |
| Speech-to-Text | Deepgram (Nova-2, streaming) |
| Text-to-Speech | ElevenLabs (Turbo v2.5, streaming) |
| LLM | Anthropic Claude (Haiku for intent/DOB, Sonnet available) |
| Frontend | React + TypeScript + Vite |
| Deployment | Render (Web Service + Worker + PostgreSQL) |

## Project Structure

```
src/
├── api/              # FastAPI app, routes, middleware
│   ├── main.py       # App entry point, CORS, lifespan
│   └── routes/
│       ├── referrals.py   # POST /api/v1/referrals
│       └── webhooks.py    # Twilio call answer/status/stream webhooks
├── audio/
│   ├── stt.py        # Deepgram streaming transcription (threaded)
│   └── tts.py        # ElevenLabs TTS with streaming output
├── conversation/
│   ├── state_machine.py   # States, transitions, context
│   └── states/            # One module per conversation phase
│       ├── identity.py    # Greeting + DOB verification
│       ├── introduction.py
│       ├── prescreen.py
│       ├── scheduling.py
│       └── escalation.py
├── db/
│   ├── models.py     # Patient, Referral, OutreachJob, CallSession
│   └── session.py    # SQLAlchemy session factory
├── llm/
│   ├── client.py     # Claude API wrapper
│   └── intent.py     # Intent classification (CONFIRM/DENY/ESCALATE/...)
├── outreach/
│   └── orchestrator.py   # Outreach cadence and job creation
├── queue/
│   ├── worker.py     # Celery app config (Redis TLS support)
│   └── tasks.py      # queue_outreach, execute_outreach_job
├── rag/
│   ├── knowledge_base.py  # Study document ingestion
│   └── retrieval.py       # Vector similarity search
└── telephony/
    ├── client.py     # Twilio API wrapper (calls + SMS)
    └── call_handler.py    # WebSocket session orchestrator

frontend/
└── src/
    └── pages/
        └── Demo.tsx  # Live demo page — enter name/DOB/phone, triggers call

tests/
└── unit/             # 68 unit tests covering all modules
```

## Call Script (Happy Path)

```
Agent: "Hi Jane, this is Sarah calling from Lynd Clinical. Your doctor
       recently referred you to us about a research study, and I'm
       calling to follow up. Is now an okay time?"

Patient: "Yes"

Agent: "Great! Before I continue, could you please confirm your date of
       birth so I can make sure I'm speaking with the right person?"

Patient: "December 1st, 1982"

Agent: "Perfect, thank you! So as I mentioned, your doctor referred you
       for a clinical research study we're coordinating. It would involve
       a short screening call with one of our study coordinators. Would
       you like to hear a little more about it?"

Patient: "Sure"

Agent: "Great! I'll ask a few quick questions that help us see whether
       the study might be a good fit. This should only take about two
       minutes."

Agent: "First — are you between 18 and 70 years old?"
Patient: "Yes"

Agent: "And have you been diagnosed with the condition your doctor
       referred you for?"
Patient: "Yes"

Agent: "Are you currently receiving treatment for that condition?"
Patient: "No"

Agent: "Thank you for sharing that. Based on your answers, it sounds like
       you could be a good fit. The next step would be a short call with
       one of our study coordinators. Would you like me to send you a
       link so you can pick a time that works best?"

Patient: "Yes please"

Agent: "I'll send you a text with a scheduling link so you can pick
       whatever time works best. Thanks so much for your time today,
       and we look forward to connecting you with the study team!"
```

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL with pgvector extension
- Redis (or Upstash)
- Twilio account with a phone number
- Deepgram API key
- ElevenLabs API key (Starter plan or above)
- Anthropic API key

### Local Development

```bash
# Clone and set up
git clone https://github.com/delbomber/lynd2.git
cd lynd2
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.api.main:app --reload --port 8000

# Start the Celery worker (separate terminal)
celery -A src.queue.worker:celery_app worker --loglevel=info

# Start the demo frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
pytest tests/unit/ -v
```

## Deployment (Render)

The project includes a `render.yaml` Blueprint for one-click deployment:

- **lynd-api** — FastAPI web service (Docker)
- **lynd-worker** — Celery background worker (Docker)
- **lynd-db** — PostgreSQL 15

Redis is hosted externally on Upstash (Render dropped managed Redis).

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis/Upstash connection string (`rediss://` for TLS) |
| `APP_BASE_URL` | Public URL of the API (e.g. `https://lynd2.onrender.com`) |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Twilio phone number (e.g. `+13186330776`) |
| `DEEPGRAM_API_KEY` | Deepgram API key |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID |
| `ANTHROPIC_API_KEY` | Anthropic API key |

### Admin Endpoints

- `GET /health` — Health check
- `POST /admin/purge-queue` — Clear all pending Celery tasks

## API

### Create Referral

```bash
curl -X POST https://lynd2.onrender.com/api/v1/referrals \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "first_name": "Jane",
      "last_name": "Smith",
      "phone": "+15551234567",
      "date_of_birth": "1982-12-01"
    },
    "study_id": "STUDY-001",
    "referring_provider": "Dr. Johnson"
  }'
```

Response:
```json
{"referral_id": 1, "status": "pending"}
```

This triggers an outbound voice call to the patient.

## License

Proprietary — Lynd Clinical
