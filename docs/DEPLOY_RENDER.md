# Deploying Lynd Voice Agent to Render

Step-by-step guide. You'll need accounts on these services before starting:

## Prerequisites — Create Accounts & Get API Keys

You need these **before** deploying. Gather all the values first.

### 1. Twilio (phone calls)
- Sign up at https://www.twilio.com
- Buy a phone number with Voice capability
- From the Console dashboard, grab:
  - **Account SID** (starts with `AC...`)
  - **Auth Token**
  - **Phone Number** (format: `+1XXXXXXXXXX`)

### 2. Deepgram (speech-to-text)
- Sign up at https://deepgram.com
- Create an API key in the dashboard
- Grab: **API Key**

### 3. ElevenLabs (text-to-speech)
- Sign up at https://elevenlabs.io
- Go to Voices, pick a voice (e.g. "Rachel"), click the voice ID icon
- Grab: **API Key** (from profile) and **Voice ID**

### 4. Anthropic (Claude AI — intent detection)
- Sign up at https://console.anthropic.com
- Create an API key
- Grab: **API Key** (starts with `sk-ant-...`)

### 5. GitHub
- Push this repo to GitHub if you haven't:
  ```bash
  git remote add origin https://github.com/YOUR_ORG/lynd2.git
  git push -u origin main
  ```

---

## Deploy to Render

### Step 1: Create a Render account
Go to https://render.com and sign up (connect your GitHub account).

### Step 2: Create PostgreSQL database
1. Dashboard → **New** → **PostgreSQL**
2. Name: `lynd-db`
3. Plan: **Starter** ($7/mo)
4. PostgreSQL version: **15**
5. Click **Create Database**
6. Wait for it to provision (~2 min)
7. Copy the **Internal Database URL** (starts with `postgresql://`)

### Step 3: Create Redis
1. Dashboard → **New** → **Redis**
2. Name: `lynd-redis`
3. Plan: **Starter** ($7/mo)
4. Click **Create Redis**
5. Copy the **Internal Redis URL** (starts with `redis://`)

### Step 4: Enable pgvector extension
1. Go to your `lynd-db` database in Render dashboard
2. Click **Shell** tab (or connect via psql)
3. Run: `CREATE EXTENSION IF NOT EXISTS vector;`

### Step 5: Deploy the API service
1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo (`lynd2`)
3. Settings:
   - **Name**: `lynd-api`
   - **Runtime**: Docker
   - **Plan**: Starter ($7/mo)
   - **Health Check Path**: `/health`
4. Add **Environment Variables** (click "Add Environment Variable" for each):

| Key | Value |
|-----|-------|
| `DATABASE_URL` | *(paste Internal Database URL from Step 2)* |
| `REDIS_URL` | *(paste Internal Redis URL from Step 3)* |
| `APP_BASE_URL` | `https://lynd-api.onrender.com` *(your actual Render URL)* |
| `TWILIO_ACCOUNT_SID` | *(from Twilio)* |
| `TWILIO_AUTH_TOKEN` | *(from Twilio)* |
| `TWILIO_PHONE_NUMBER` | *(from Twilio, e.g. +15551234567)* |
| `DEEPGRAM_API_KEY` | *(from Deepgram)* |
| `ELEVENLABS_API_KEY` | *(from ElevenLabs)* |
| `ELEVENLABS_VOICE_ID` | *(from ElevenLabs)* |
| `ANTHROPIC_API_KEY` | *(from Anthropic)* |
| `ENVIRONMENT` | `production` |

5. Click **Create Web Service**
6. Wait for build & deploy (~3-5 min)

### Step 6: Run database migrations
Once the API is deployed:
1. Go to `lynd-api` → **Shell** tab
2. Run:
   ```bash
   DATABASE_URL=$DATABASE_URL alembic upgrade head
   ```

### Step 7: Deploy the Celery worker
1. Dashboard → **New** → **Background Worker**
2. Connect the same GitHub repo
3. Settings:
   - **Name**: `lynd-worker`
   - **Runtime**: Docker
   - **Docker Command**: `celery -A src.queue.worker:celery_app worker --loglevel=info`
   - **Plan**: Starter ($7/mo)
4. Add the **same environment variables** as the API service (Step 5)
5. Click **Create Background Worker**

### Step 8: Configure Twilio webhooks
1. Go to Twilio Console → your phone number → **Configure**
2. Under "A Call Comes In", you don't need to set anything (we make outbound calls, not inbound)
3. The webhook URLs are automatically constructed per-call by the app

### Step 9: Verify it works
1. Check the health endpoint:
   ```
   curl https://lynd-api.onrender.com/health
   ```
   Should return: `{"status":"ok"}`

2. Submit a test referral:
   ```bash
   curl -X POST https://lynd-api.onrender.com/api/v1/referrals \
     -H "Content-Type: application/json" \
     -d '{
       "patient": {
         "first_name": "Test",
         "last_name": "Patient",
         "phone": "+1YOUR_PHONE_NUMBER",
         "date_of_birth": "1990-01-15"
       },
       "study_id": "STUDY-001",
       "referring_provider": "Dr. Smith"
     }'
   ```
   Replace `+1YOUR_PHONE_NUMBER` with your actual cell phone. You should receive a call within seconds.

---

## Costs Summary

| Service | Plan | Monthly Cost |
|---------|------|-------------|
| Render Web Service (API) | Starter | $7 |
| Render Background Worker (Celery) | Starter | $7 |
| Render PostgreSQL | Starter | $7 |
| Render Redis | Starter | $7 |
| **Render Total** | | **$28/mo** |
| Twilio (calls) | Pay-as-you-go | ~$0.02/min |
| Deepgram (STT) | Pay-as-you-go | ~$0.0043/min |
| ElevenLabs | Starter | $5/mo (30k chars) |
| Anthropic (Claude) | Pay-as-you-go | ~$0.001/call |

**Estimated pilot cost for 20-50 referrals/week:** ~$40-50/mo total

---

## Troubleshooting

### "Application failed to respond"
- Check Render logs (Dashboard → your service → **Logs**)
- Most common: missing environment variable

### Calls not going out
- Check the worker logs (lynd-worker → Logs)
- Verify Redis is connected (worker will error if not)
- Verify Twilio credentials are correct

### Call connects but no AI conversation
- Check API logs during a call for WebSocket errors
- Verify Deepgram and ElevenLabs API keys are set
- The `APP_BASE_URL` must match your actual Render URL exactly (with `https://`)

### Database migration errors
- Connect to Render Shell and run `alembic upgrade head`
- Check that pgvector extension is enabled: `SELECT * FROM pg_extension WHERE extname = 'vector';`

---

## Updating After Code Changes

1. Push to GitHub: `git push origin main`
2. Render auto-deploys on push (both API and worker)
3. If you changed models, run migrations via Shell: `alembic upgrade head`
