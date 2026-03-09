# Demo Day Checklist — Thursday

## Service Limits to Verify

| Service | Where to Check | What to Look For |
|---------|---------------|------------------|
| ElevenLabs | elevenlabs.io/app/usage | Character usage vs. plan limit (free = 10K/mo) |
| Anthropic | console.anthropic.com | Credit balance, API key active |
| Twilio | console.twilio.com/billing | Account balance, trial vs. paid, verified numbers |
| Deepgram | console.deepgram.com | Credit remaining (free = $200) |
| Render | dashboard.render.com | Services running, no deploy failures |
| Upstash Redis | console.upstash.com | Daily command count (free = 10K/day) |

## Day Before (Wednesday)

- [ ] Run one full end-to-end test call to the demo phone
- [ ] Check ElevenLabs character usage — upgrade to Starter ($5/mo) if close to limit
- [ ] Check Anthropic credit balance
- [ ] Check Twilio balance — confirm paid account or that demo phone is verified
- [ ] Verify Render services are running: `curl https://<your-app>.onrender.com/health`
- [ ] Cancel any stale outreach jobs: `POST /admin/cancel-all-jobs`
- [ ] Purge the Celery queue: `POST /admin/purge-queue`
- [ ] Confirm the demo page loads and API URL is saved in settings

## 30 Minutes Before Demo

- [ ] Hit `/health` endpoint to warm up Render (starter plan can be slow after idle)
- [ ] Open the demo page, verify settings gear has the correct Pilot Server URL
- [ ] Do one quick test call — confirm greeting plays, DOB verifies, full flow works
- [ ] Open Render logs in a browser tab (for live debugging if needed)
- [ ] Silence your own phone notifications so they don't interrupt the demo call

## During the Demo

- [ ] Pre-fill the form: name, DOB (1982-12-01), Dr. Jones, phone number
- [ ] Click "Call Me" — phone should ring within 30 seconds
- [ ] Walk the room through: greeting -> DOB verification -> intro -> pre-screen -> scheduling
- [ ] If call doesn't connect within 45 seconds, check Render logs for errors

## If Something Goes Wrong

- [ ] Have a screen recording of a successful call ready as backup
- [ ] If ElevenLabs is down: the call will still work but TTS responses may fail silently
- [ ] If the call goes to voicemail: try again — Twilio AMD detection can misfire on first attempt
- [ ] If DOB verification fails: say a clear date like "December first, nineteen eighty-two"
- [ ] If Render is slow: explain cold start, retry — second call will be faster

## Known Quirks

- Deepgram sometimes transcribes background noise as words — this can burn a DOB attempt
- First call after long idle may have slightly longer response latency
- Twilio trial accounts can ONLY call verified phone numbers
- The agent's name is "Sarah" — it will introduce itself that way
- Say "speak to a person" at any time to trigger escalation
