# Local Docker Testing — CareerClaw + OpenClaw Agent

This guide documents exactly how to run **CareerClaw inside a local OpenClaw agent** using Docker, connect it to Telegram, and test the full skill end-to-end.

The setup is fully isolated:

- The OpenClaw **gateway + agent** run in Docker.
- The CareerClaw **sandbox** runs in Docker.
- No access to your Windows host filesystem **except** the explicit bind mount of `.careerclaw/`.
- CareerClaw source code is baked into the sandbox image at build time.

> **Local testing only.** This is not part of the ClawHub publication flow.  
> Docker files are committed for transparency and contributor use.

---

## Architecture Overview

You are running **two layers**:

### Layer 1 — OpenClaw Gateway + Agent
- Handles Telegram messaging
- Runs the agent model (recommended: `openai/gpt-5.2`)
- Stores agent configuration/state in a named Docker volume mounted at `/home/node/.openclaw`

### Layer 2 — CareerClaw Sandbox
- Runs `python -m careerclaw.briefing`
- Isolated Python 3.12 environment (custom image: `careerclaw-sandbox:local`)
- Writes runtime data only to `.careerclaw/` (profile, tracking, run logs, cached resume intel)

**Important:** The agent model selection is **not** controlled by `.env`.  
It is stored in `/home/node/.openclaw` and configured via `openclaw-cli config set`.

---

## Prerequisites

- Docker Desktop for Windows with WSL2 backend enabled
- WSL2 terminal (Ubuntu) — all commands in this guide run from WSL2
- A Telegram account
- An **OpenAI API key** (recommended; used by default agent model)
- Optional: Anthropic API key (fallback provider)
- CareerClaw repository cloned locally

---

## File Structure

These files are part of the Docker setup:

```text
careerclaw/
├── docker/
│   ├── Dockerfile.sandbox      ← Python 3.12 + CareerClaw sandbox image
│   ├── docker-compose.yml      ← OpenClaw gateway + wiring
│   └── openclaw.yml            ← Agent config (sandbox mode, tools)
├── .env.example                ← Template for secrets (committed)
├── .env                        ← Your actual secrets (gitignored)
└── DOCKER.md                   ← This file
```

`.env` is gitignored and must never be committed.

---

## Step 1 — Fix Docker Credential Helper (WSL2)

Docker Desktop on Windows can set a credential helper that breaks inside WSL2, causing image pulls to fail with `error getting credentials`.

Check:

```bash
cat ~/.docker/config.json
```

If you see `desktop.exe` as a credential store, fix it:

```bash
# Replace the file with an empty JSON object
echo '{}' > ~/.docker/config.json
```

> This affects only WSL2. Docker Desktop on Windows is unaffected.

---

## Step 2 — Build the OpenClaw Base Images

The official OpenClaw repo provides a setup script that builds:

- `openclaw:local` (gateway image)
- `openclaw-sandbox:bookworm-slim` (base sandbox image)

Clone OpenClaw **outside** the CareerClaw repo:

```bash
git clone https://github.com/openclaw/openclaw.git ~/openclaw
cd ~/openclaw
./docker-setup.sh
```

Recommended wizard answers:

| Prompt | Answer |
|--------|--------|
| Model provider | **OpenAI (recommended)** |
| API key | Your OpenAI key (`sk-...`) |
| Messaging channel | Skip — Telegram is configured later |
| Tailscale / mesh networking | No |
| Optional features | Skip |

Verify images exist:

```bash
docker images | grep openclaw
# Expected:
# openclaw              local
# openclaw-sandbox      bookworm-slim
```

> Re-run `./docker-setup.sh` if either image is missing.

---

## Step 3 — Build the CareerClaw Sandbox Image

This builds a custom sandbox image extending `openclaw-sandbox:bookworm-slim` with Python 3.12, CareerClaw, and required packages.

Run from the **CareerClaw repo root**:

```bash
cd /path/to/careerclaw

docker build -f docker/Dockerfile.sandbox -t careerclaw-sandbox:local .
```

Verify:

```bash
docker images | grep careerclaw-sandbox
# Expected: careerclaw-sandbox   local
```

> Rebuild this image any time you update CareerClaw source code.

---

## Step 4 — Configure Environment Variables

From the CareerClaw repo root:

```bash
cp .env.example .env
nano .env
```

Fill in the required values:

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENCLAW_GATEWAY_TOKEN` | Yes | Gateway auth token |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `OPENAI_API_KEY` | Recommended | Agent provider key (default model) |
| `ANTHROPIC_API_KEY` | Optional | Fallback provider key |
| `CAREERCLAW_PRO_KEY` | Optional | Pro license key (Polar) |
| `CAREERCLAW_LLM_KEY` | Optional | Override key for Pro drafts |

Failover + retry defaults (recommended):

```env
CAREERCLAW_LLM_CHAIN=openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6
CAREERCLAW_LLM_MAX_RETRIES=2
CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS=2
```

### Finding `OPENCLAW_GATEWAY_TOKEN`

Depending on how your OpenClaw setup is stored, you can retrieve the token from inside the gateway container:

```bash
docker compose -f docker/docker-compose.yml --env-file .env exec -T openclaw-gateway   sh -lc 'cat /home/node/.openclaw/openclaw.json | grep -i token'
```

---

## Step 5 — Create a Telegram Bot

1. Open Telegram and search **@BotFather** (blue checkmark)
2. Click **START**, then send `/newbot`
3. Enter a display name (e.g., `CareerClaw Test`)
4. Enter a username ending in `bot` (e.g., `careerclaw_orestes_bot`)
5. BotFather replies with a token — copy it into `.env` as `TELEGRAM_BOT_TOKEN`

> Keep the token secret. If it’s exposed, regenerate it via `/revoke` in @BotFather.

---

## Step 6 — Fix Volume Permissions (First Run Only)

The OpenClaw named volume must be owned by the non-root `node` user (UID 1000) that the gateway runs as.

Run once after the volume is created:

```bash
docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data
```

> Repeat this if you see `EACCES: permission denied` errors in gateway logs.

---

## Step 7 — Start the Gateway

All `docker compose` commands require `--env-file .env` because the compose file lives in `docker/` but `.env` is in the repo root.

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

Watch logs:

```bash
docker compose -f docker/docker-compose.yml --env-file .env logs openclaw-gateway -f
```

Look for:

```text
[telegram] starting provider
[gateway] listening on ws://127.0.0.1:18789
[gateway] agent model: openai/gpt-5.2
```

Press `Ctrl+C` to stop tailing logs (the gateway keeps running).

---

## Step 8 — Pair Your Telegram Account

Pairing links your Telegram account to the bot so only you can send commands.

### 8a — Initiate from Telegram
Open your bot in Telegram and send any message (e.g., `hi`). The bot should reply with a pairing code.

### 8b — Approve via CLI
List pending requests:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli pairing list
```

Approve (replace `CODE`):

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli pairing approve CODE
```

Expected output: `Approved telegram sender <your-id>.`

Send `hi` again — it should now respond as the OpenClaw agent.

---

## Step 9 — Configure Sandbox Mode + Image

Set the custom sandbox image:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config set agents.defaults.sandbox.docker.image "careerclaw-sandbox:local"
```

Enable sandbox mode:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config set agents.defaults.sandbox.mode "non-main"
```

Verify:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config get agents.defaults.sandbox
```

Restart gateway to apply:

```bash
docker compose -f docker/docker-compose.yml --env-file .env down
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

> In this setup, `.env` values are forwarded via Docker Compose to the gateway.  
> If your OpenClaw version requires explicitly setting sandbox env vars via config, you can do so with:
>
> `config set agents.defaults.sandbox.docker.env.<NAME> "<VALUE>"`  
>
> Note: this stores the value in the OpenClaw config volume.

---

## Step 10 — Set Agent Model (Recommended)

Set the agent model:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config set agents.defaults.model.primary openai/gpt-5.2
```

Verify:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config get agents.defaults.model.primary
```

Restart gateway after model changes:

```bash
docker compose -f docker/docker-compose.yml --env-file .env restart openclaw-gateway
```

---

## Step 11 — Install CareerClaw and Run a Briefing

Install the skill (send in Telegram):

```text
install skill from https://github.com/orestes-garcia-martinez/careerclaw
```

Dry run briefing (no tracking written):

```text
Run a dry-run job briefing
```

Real briefing (saves tracking):

```text
Run a job briefing
```

Expected behavior:
- Top job matches (RemoteOK + HN Who’s Hiring)
- Fit analysis and gap analysis (Pro only)
- Deterministic drafts (Free) or enhanced drafts (Pro, if configured)
- Tracking written to `.careerclaw/`

---

## Quick Command Reference

All commands run from the CareerClaw repo root in WSL2.

| Command | What it does |
|--------|--------------|
| `docker compose ... up -d openclaw-gateway` | Start the gateway |
| `docker compose ... down` | Stop gateway + network |
| `docker compose ... logs openclaw-gateway -f` | Stream gateway logs |
| `docker compose ... run --rm openclaw-cli <cmd>` | Run a one-off CLI command |
| `docker compose ... restart openclaw-gateway` | Restart gateway after config changes |
| `docker build -f docker/Dockerfile.sandbox -t careerclaw-sandbox:local .` | Rebuild sandbox after code changes |
| `docker images \| grep openclaw` | List OpenClaw images |
| `docker ps \| grep openclaw` | List running OpenClaw containers |
| `docker volume rm careerclaw-openclaw-config` | Reset gateway state (destructive) |
| `docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data` | Fix volume permissions |

> Every `docker compose` command requires: `-f docker/docker-compose.yml --env-file .env`

---

## Isolation Contract

| Path | Access | Purpose |
|------|--------|---------|
| `.careerclaw/` | Read + Write | Profile, resume, tracking, run logs |
| `careerclaw/` source | None at runtime | Baked into sandbox image |
| `docker/` files | None at runtime | Used by gateway only |
| Windows filesystems | None | Not mounted |
| Internet | Outbound allowed | RemoteOK + HN APIs |

---

## Troubleshooting

### `error getting credentials` when pulling images
Fix WSL2 Docker credential helper (Step 1).

### `EACCES: permission denied` in gateway logs
Fix volume ownership (Step 6), then restart.

### Env vars show “variable is not set”
Always use `--env-file .env` because the compose file lives in `docker/`.

### Bot does not respond in Telegram
Check gateway logs for `[telegram] starting provider`. If missing:
- `TELEGRAM_BOT_TOKEN` is missing/invalid
- volume permissions are broken (run Step 6)

### Agent says “No API key found for provider openai”
Add `OPENAI_API_KEY` to `.env` and ensure it is forwarded into the gateway container.

### CareerClaw drafts not LLM-enhanced
Confirm:
- Pro is enabled (`CAREERCLAW_PRO_KEY` valid)
- Resume intelligence is present
- Either `CAREERCLAW_LLM_KEY` is set OR `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` exists
- Failover chain env vars are present

### Sandbox container not starting / wrong image
Verify:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli   config get agents.defaults.sandbox
```

Make sure:
- `docker.image` is `careerclaw-sandbox:local`
- `mode` is `non-main`

### `careerclaw-sandbox:local` image not found
Rebuild it (Step 3).

---

