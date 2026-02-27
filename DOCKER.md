# Local Docker Testing — CareerClaw + OpenClaw Agent

This guide documents exactly how to run **CareerClaw inside a local OpenClaw agent** using Docker, connect it to Telegram, and test the full skill end to end.

The setup is fully isolated:

- The OpenClaw **gateway + agent** run in Docker.
- The CareerClaw **sandbox** runs in Docker.
- No access to your Windows host filesystem **except** the explicit bind mount of `.careerclaw/`.
- CareerClaw source code is baked into the sandbox image at build time.

> **Local testing only.** This is not part of the ClawHub publication flow.
> Docker files are committed for transparency and contributor use.

---

## Architecture Overview

### Layer 1 — OpenClaw Gateway + Agent
- Handles Telegram messaging
- Runs the agent model (set via `openclaw-cli config set` — not via `.env`)
- Stores agent config + state in the named Docker volume `careerclaw-openclaw-config` at `/home/node/.openclaw`
- Reads `docker/openclaw.yml` on startup (mounted read-only) for sandbox image, resource limits, and CareerClaw env var forwarding

### Layer 2 — CareerClaw Sandbox
- Runs `python -m careerclaw.briefing`
- Custom image: `openclaw-sandbox:careerclaw` (built from `docker/Dockerfile.sandbox`)
- Writes runtime data only to `.careerclaw/`
- Receives CareerClaw env vars forwarded from the gateway via `docker/openclaw.yml`

> ⚠️ **Important:** Two config values — `agents.defaults.sandbox.mode` and `agents.defaults.model.primary` — are stored in the named volume, NOT read from `openclaw.yml`. They must be set via `openclaw-cli config set` after every volume reset.

---

## Prerequisites

- Docker Desktop for Windows with WSL2 backend enabled
- WSL2 terminal (Ubuntu) — all commands run from WSL2
- A Telegram account
- An OpenAI API key **or** Anthropic API key for the OpenClaw agent
- CareerClaw repository cloned locally

---

## File Structure

```text
careerclaw/
├── docker/
│   ├── Dockerfile.sandbox      ← extends openclaw:local with Python + CareerClaw
│   ├── docker-compose.yml      ← gateway wiring + env forwarding
│   └── openclaw.yml            ← sandbox image, resource limits, env vars
├── .env.example                ← secrets template (committed)
├── .env                        ← your actual secrets (gitignored)
├── update.sh                   ← update SKILL.md + rebuild sandbox after code changes
└── DOCKER.md                   ← this file
```

---

## Step 1 — Fix Docker Credential Helper (WSL2)

Docker Desktop on Windows sets a credential helper that breaks inside WSL2.

Check:

```bash
cat ~/.docker/config.json
```

If you see `desktop.exe` as a credential store, fix it:

```bash
echo '{}' > ~/.docker/config.json
```

> This must be done before any `docker run` or image pull. It only affects WSL2.

---

## Step 2 — Build the OpenClaw Base Image

Clone OpenClaw **outside** the CareerClaw repo:

```bash
git clone https://github.com/openclaw/openclaw.git ~/openclaw
cd ~/openclaw
./docker-setup.sh
```

Wizard answers:

| Prompt | Answer |
|--------|--------|
| Model provider | OpenAI or Anthropic |
| API key | Your key |
| Messaging channel | Skip — Telegram is configured later |
| Tailscale / mesh networking | No |
| Configure skills now? | **No** |
| Any other optional features | Skip |

Verify:

```bash
docker images | grep openclaw
# Expected: openclaw   local   ...
```

> ⚠️ `openclaw-sandbox:bookworm-slim` is **no longer produced** as a separate tagged image in recent OpenClaw versions. Only `openclaw:local` is needed — do not look for the bookworm-slim image.

---

## Step 3 — Build the CareerClaw Sandbox Image

This extends `openclaw:local` with Python 3.12, CareerClaw, `anthropic`, and `openai` pre-installed.

> ⚠️ Verify `docker/Dockerfile.sandbox` starts with `FROM openclaw:local` — **not** `FROM openclaw-sandbox:bookworm-slim`. Update it if your repo still has the old value.

Run from the **CareerClaw repo root** (the build context must be `.`):

```bash
cd /mnt/d/02_clawhub-monetization/careerclaw

docker build -f docker/Dockerfile.sandbox -t openclaw-sandbox:careerclaw .
```

Verify:

```bash
docker images | grep careerclaw
# Expected: openclaw-sandbox   careerclaw   ...
```

> ⚠️ **Local testing vs ClawHub deployment:** Rebuilding this image updates the **ClawHub deployment artifact** — it does NOT update the code the gateway uses during local testing. For local testing, the gateway clones your GitHub repo and runs code from there. See "Updating CareerClaw After Code Changes" below for the correct workflow.

---

## Step 4 — Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

| Variable | Required | Notes |
|----------|----------|-------|
| `OPENCLAW_GATEWAY_TOKEN` | Yes | From `~/.openclaw/openclaw.json` after first gateway start |
| `TELEGRAM_BOT_TOKEN` | Yes | From @BotFather |
| `OPENAI_API_KEY` | Recommended | Powers the OpenClaw agent |
| `ANTHROPIC_API_KEY` | Optional | Fallback agent provider |
| `GITHUB_TOKEN` | Recommended | Prevents GitHub API rate limits on skill installs |
| `CAREERCLAW_PRO_KEY` | Optional | Pro license key |
| `CAREERCLAW_OPENAI_KEY` | Optional | **Must be explicitly set** for Pro LLM drafts via OpenAI |
| `CAREERCLAW_ANTHROPIC_KEY` | Optional | **Must be explicitly set** for Pro LLM drafts via Anthropic |

> ⚠️ **`CAREERCLAW_OPENAI_KEY` and `CAREERCLAW_ANTHROPIC_KEY` must have actual values if you want LLM-enhanced drafts.** If left empty, CareerClaw falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — your agent keys — which may cause billing confusion or rate limit collisions.

LLM failover chain:

```env
CAREERCLAW_LLM_CHAIN=openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6
CAREERCLAW_LLM_MAX_RETRIES=2
CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS=2
```

> If your Anthropic account has a negative credit balance, remove `anthropic/claude-sonnet-4-6` from the chain to avoid billing errors.

---

## Step 5 — Create a Telegram Bot

1. Open Telegram, search **@BotFather** (blue checkmark)
2. Send `/newbot`
3. Enter a display name, e.g. `CareerClaw Test`
4. Enter a username ending in `bot`, e.g. `careerclaw_yourname_bot`
5. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`

> If the token is exposed, regenerate via `/revoke` in @BotFather. Select your bot from the list — do not type the name manually.

---

## Step 6 — Fix Volume Permissions

The named volume must be owned by UID 1000 (the non-root `node` user the gateway runs as):

```bash
docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data
```

> ⚠️ Run this every time the volume is deleted and recreated. Without it you will see `EACCES: permission denied` errors and the gateway will fail.

---

## Step 7 — Start the Gateway

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

Watch logs to confirm a clean start:

```bash
docker compose -f docker/docker-compose.yml --env-file .env logs openclaw-gateway -f
```

Look for:

```text
[telegram] starting provider (@your_bot_name)
[gateway] listening on ws://127.0.0.1:18789
```

Press `Ctrl+C` to stop following logs (gateway keeps running).

---

## Step 8 — Pair Your Telegram Account

### 8a — Initiate from Telegram
Open your bot and send any message (e.g. `hi`). The bot replies with a pairing code.

### 8b — Approve via CLI

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli pairing approve CODE
```

Expected: `Approved telegram sender <your-id>.`

> ⚠️ Pairing is stored in the named volume. If the volume is reset, you must pair again.

---

## Step 9 — Apply Post-Volume Config (Always Required)

> ⚠️ This step is **always required** after any volume reset. `openclaw.yml` sets `docker.image` from file but does NOT persist `mode`. The agent model is also wiped on every reset.

```bash
# 1. Set sandbox mode
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.sandbox.mode "non-main"

# 2. Set agent model
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.model.primary "openai/gpt-5.2"

# 3. Restart to apply
docker compose -f docker/docker-compose.yml --env-file .env restart openclaw-gateway
```

Verify:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config get agents.defaults.sandbox

# Expected:
# {
#   "mode": "non-main",
#   "docker": { "image": "openclaw-sandbox:careerclaw" }
# }
```

---

## Step 10 — Install CareerClaw Skill

### Option A — GitHub install (may hit rate limits)

Send to your Telegram bot:

```
Reinstall skill from https://github.com/orestes-garcia-martinez/careerclaw
```

### Option B — Raw URL (always works, recommended)

Send to your Telegram bot:

```
Update the careerclaw skill. Fetch the new SKILL.md from
https://raw.githubusercontent.com/orestes-garcia-martinez/careerclaw/main/SKILL.md
and replace the current skill definition.
```

---

## Step 11 — Run a Briefing

Dry run (nothing saved to tracking):

```
Run a dry-run job briefing
```

Real run (saves to `.careerclaw/tracking.json`):

```
Run a job briefing
```

Expected output:
- Top job matches (RemoteOK + HN Who's Hiring)
- Score, matched skills, location and fit warnings
- Template drafts (Free) or LLM-enhanced drafts (Pro)
- `Pro tier ✓` shown if `CAREERCLAW_PRO_KEY` is valid

---

## After Every Volume Reset — Checklist

The named volume stores agent state. Any time it is deleted or recreated, run these in order:

```bash
# 1. Fix permissions
docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data

# 2. Start gateway
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway

# 3. Set sandbox mode
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.sandbox.mode "non-main"

# 4. Set agent model
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.model.primary "openai/gpt-5.2"

# 5. Restart
docker compose -f docker/docker-compose.yml --env-file .env restart openclaw-gateway

# 6. Pair Telegram (get code from bot first — send "hi")
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  pairing approve CODE

# 7. Reinstall skill — send this to your Telegram bot:
# Update the careerclaw skill. Fetch the new SKILL.md from
# https://raw.githubusercontent.com/orestes-garcia-martinez/careerclaw/main/SKILL.md
# and replace the current skill definition.
```

---

## Updating CareerClaw After Code Changes

> ⚠️ **Two separate update paths exist** depending on what you are updating.

### Local testing — gateway runs from a cloned GitHub repo

The gateway clones your repo into `/home/node/.openclaw/workspace/.careerclaw-repo/`
and runs Python code directly from there. Rebuilding the sandbox image has **no effect**
on local testing. The correct workflow is:

1. `git push` your changes to GitHub
2. `./update.sh --repo` — pulls latest code into the gateway's repo clone
3. `./update.sh --skill` — if `SKILL.md` also changed

No gateway restart is needed after a `--repo` pull.

### ClawHub deployment — sandbox image is the artifact

When publishing to ClawHub, the `openclaw-sandbox:careerclaw` image is what gets deployed.
Rebuild it after any Python source change:

1. `git push` your changes to GitHub
2. `./update.sh --code` — rebuilds `openclaw-sandbox:careerclaw`
3. `./update.sh --skill` — if `SKILL.md` also changed

```bash
./update.sh --repo    # pull latest code into gateway repo (local testing)
./update.sh --skill   # SKILL.md only (both workflows)
./update.sh --code    # rebuild sandbox image (ClawHub deployment only)
./update.sh           # rebuild image + prompt to refresh SKILL.md
```

| What changed | Local testing | ClawHub deployment |
|---|---|---|
| Python source only | `./update.sh --repo` | `./update.sh --code` |
| `SKILL.md` only | `./update.sh --skill` | `./update.sh --skill` |
| Both | `./update.sh --repo && ./update.sh --skill` | `./update.sh` |

---

## Rate Limits

| Limit | Cause | Fix |
|-------|-------|-----|
| GitHub API (60 req/hr unauthenticated) | Skill installs + git activity | Set `GITHUB_TOKEN` in `.env`. Use raw URL for SKILL.md. |
| Anthropic API (daily token quota) | Heavy agent usage | Switch agent to `openai/gpt-5.2`. Resets at midnight UTC. |
| HN Firebase | Rapid repeated briefings | Wait 15 minutes. |

**Diagnosing which limit you hit:** Send `What is 2 + 2?` to the bot.
- Answers `4` → agent is fine; error is in CareerClaw enhancement layer.
- Also fails → the agent itself is hitting its provider limit.

**Rate limit vs billing error:**
- `API rate limit reached` → quota exhausted, resets automatically.
- `API provider returned a billing error` → no credits. Top up or remove that provider from `CAREERCLAW_LLM_CHAIN`.

---

## Quick Command Reference

All commands from the CareerClaw repo root in WSL2.

| Command | What it does |
|---------|-------------|
| `docker compose ... up -d openclaw-gateway` | Start the gateway |
| `docker compose ... down` | Stop gateway + remove network |
| `docker compose ... restart openclaw-gateway` | Restart after config changes |
| `docker compose ... logs openclaw-gateway -f` | Stream gateway logs |
| `docker compose ... run --rm openclaw-cli <cmd>` | Run a CLI command |
| `docker build -f docker/Dockerfile.sandbox -t openclaw-sandbox:careerclaw .` | Rebuild sandbox image |
| `docker images \| grep openclaw` | List OpenClaw images |
| `docker ps \| grep openclaw` | List running containers |
| `docker volume rm careerclaw-openclaw-config` | Delete volume (destructive — triggers full reset) |
| `docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data` | Fix volume permissions |

> Every `docker compose` command requires: `-f docker/docker-compose.yml --env-file .env`

---

## Isolation Contract

| Path | Access | Purpose |
|------|--------|---------|
| `.careerclaw/` | Read + Write | Profile, resume, tracking, run logs |
| `careerclaw/` source | None at runtime | Baked into sandbox image at build time |
| `docker/openclaw.yml` | Read-only (gateway) | Sandbox image + resource limits + env forwarding |
| Windows filesystems | None | Not mounted |
| Internet | Outbound allowed | RemoteOK + HN APIs |

---

## Troubleshooting

### `error getting credentials` when pulling images
Fix WSL2 credential helper (Step 1). Must be done before any `docker run`.

### `EACCES: permission denied` in gateway logs
Run the `chown` command from Step 6, then restart the gateway.

### `openclaw-sandbox:bookworm-slim` not found during build
Update `Dockerfile.sandbox`: change `FROM openclaw-sandbox:bookworm-slim` to `FROM openclaw:local`. Rebuild.

### Bot does not respond / "OpenClaw: access not configured"
Volume was reset — pairing lost. Send `hi` to the bot, get the new code, run `pairing approve CODE`.

### Agent says "I don't know what a job briefing is"
Skill was lost on volume reset. Reinstall using Option B (raw URL, Step 10).

### Agent says "Only the skill definition exists — no Python package"
Sandbox mode is not set. Run Step 9 (`config set agents.defaults.sandbox.mode "non-main"`), then restart.

### Drafts are template-only despite Pro key being set
`CAREERCLAW_OPENAI_KEY` or `CAREERCLAW_ANTHROPIC_KEY` is empty in `.env`. Fill in the actual key values and restart the gateway.

### `API provider returned a billing error`
A provider key has no credits. Check:
- OpenAI: https://platform.openai.com/settings/organization/billing
- Anthropic: https://console.anthropic.com/settings/billing

If Anthropic is negative, remove `anthropic/claude-sonnet-4-6` from `CAREERCLAW_LLM_CHAIN` in `.env` and restart.

### Sandbox `mode` or agent model missing after volume reset
Both are stored in the volume, not in `openclaw.yml`. Always re-run Step 9 after any volume reset.

### Gateway hangs during `update.sh`
Run the restart commands manually:
```bash
docker compose -f docker/docker-compose.yml --env-file .env down
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```
