# Local Docker Testing — CareerClaw + OpenClaw Agent

This guide documents exactly how to run CareerClaw inside a local
OpenClaw agent using Docker, connect it to Telegram, and test the full
skill end to end. The setup is fully isolated — the container has no
access to your Windows host files except `.careerclaw/`.

**This setup is for local testing only.** It is not part of the ClawHub
publication flow. The Docker files are committed to the repo for
transparency and contributor use.

---

## Prerequisites

- Docker Desktop for Windows with WSL2 backend enabled
- WSL2 terminal (Ubuntu) — all commands in this guide run from WSL2
- A Telegram account
- An Anthropic API key (powers the OpenClaw agent)
- The CareerClaw repository cloned locally

---

## File Structure

These files are added to the repo root for the Docker setup:

```
careerclaw/
├── docker/
│   ├── Dockerfile.sandbox      ← Python 3.12 + CareerClaw sandbox image
│   ├── docker-compose.yml      ← Gateway + sandbox wired together
│   └── openclaw.yml            ← Agent config (sandbox mode, tools)
├── .env.example                ← Template for all secrets (committed)
├── .env                        ← Your actual secrets (gitignored)
└── DOCKER.md                   ← This file
```

> `.env` is gitignored and will never be committed. Only `.env.example`
> is committed.

---

## Step 1 — Fix Docker Credential Helper (WSL2)

Docker Desktop on Windows sets a credential helper that breaks inside
WSL2, causing image pulls to fail with `error getting credentials`. Fix
it before doing anything else:

```bash
# Check what's set
cat ~/.docker/config.json
# If you see: { "credsStore": "desktop.exe" } — fix it

echo '{}' > ~/.docker/config.json
```

> This only affects WSL2. Docker Desktop on Windows is unaffected.

---

## Step 2 — Build the OpenClaw Base Images

The official OpenClaw repo provides a setup script that builds the
`openclaw:local` gateway image and the `openclaw-sandbox:bookworm-slim`
base image that `Dockerfile.sandbox` extends.

Clone OpenClaw **outside** the CareerClaw repo — it is a separate project:

```bash
# Clone to your WSL2 home directory (not inside CareerClaw)
git clone https://github.com/openclaw/openclaw.git ~/openclaw
cd ~/openclaw
./docker-setup.sh
```

Answer the setup wizard as follows:

| Prompt | Answer |
|--------|--------|
| Model provider | Anthropic |
| API key | Your Anthropic key (`sk-ant-...`) |
| Messaging channel | Skip — Telegram is added in Step 5 |
| Tailscale / mesh networking | No |
| Any other optional features | Skip |

Verify both base images were created:

```bash
docker images | grep openclaw
# Expected:
# openclaw              local              ...
# openclaw-sandbox      bookworm-slim      ...
```

> Both images must be present before Step 3. Re-run `./docker-setup.sh`
> if either is missing.

---

## Step 3 — Build the CareerClaw Sandbox Image

This builds a custom image extending `openclaw-sandbox:bookworm-slim`
with Python 3.12, CareerClaw, and the `anthropic`/`openai` packages
pre-installed. This is the image that runs `python -m careerclaw.briefing`
in isolation.

Run from the **CareerClaw repo root** — the build context must be `.`
so that `COPY careerclaw/` and `COPY pyproject.toml` resolve correctly:

```bash
cd /path/to/careerclaw

# -f docker/Dockerfile.sandbox  →  Dockerfile location
# -t careerclaw-sandbox:local   →  tag for the resulting image
# .                             →  build context = repo root (required)
docker build -f docker/Dockerfile.sandbox -t careerclaw-sandbox:local .
```

Verify:

```bash
docker images | grep careerclaw-sandbox
# Expected: careerclaw-sandbox   local   ...
```

> Rebuild this image any time you update the CareerClaw source code.

---

## Step 4 — Configure Environment Variables

```bash
# From the CareerClaw repo root
cp .env.example .env
nano .env
```

Fill in the following values:

| Variable | Value |
|----------|-------|
| `OPENCLAW_GATEWAY_TOKEN` | Found in `~/.openclaw/openclaw.json` — see below |
| `TELEGRAM_BOT_TOKEN` | From @BotFather — see Step 5 |
| `ANTHROPIC_API_KEY` | Your Anthropic key — powers the OpenClaw agent itself |
| `CAREERCLAW_LLM_KEY` | Your Anthropic or OpenAI key for Pro drafts (optional) |
| `CAREERCLAW_LLM_PROVIDER` | `anthropic` (default) or `openai` |
| `CAREERCLAW_LLM_MODEL` | Leave blank to use the provider default |

To find the gateway token:

```bash
cat ~/.openclaw/openclaw.json | grep -i token
# Look for: "token": "1cdd27b0..."
```

---

## Step 5 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather** (blue checkmark)
2. Click **START**, then send `/newbot`
3. Enter a display name, e.g. `CareerClaw Test`
4. Enter a username ending in `bot`, e.g. `careerclaw_orestes_bot`
5. BotFather replies with a token — copy it into `.env` as `TELEGRAM_BOT_TOKEN`

> Keep the token secret. If it's ever exposed, regenerate it via
> `/revoke` in @BotFather — select your bot from the button list
> (don't type the name manually).

---

## Step 6 — Fix Volume Permissions

The OpenClaw named volume must be owned by the non-root `node` user
(UID 1000) that the gateway runs as. Without this fix, the gateway
cannot write its config files and Telegram will not connect.

```bash
# Alpine is a tiny 5MB image used as a throwaway tool to run chown.
# --rm removes it immediately after it exits.
docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data
```

> Run this once after first creating the volume. Repeat it if you see
> `EACCES: permission denied` errors in the gateway logs.

---

## Step 7 — Start the Gateway

All `docker compose` commands require `--env-file .env` because the
compose file lives in `docker/` but `.env` is at the repo root. Docker
Compose resolves env files relative to the compose file location, not
the working directory.

```bash
# From the CareerClaw repo root
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

Watch the logs to confirm a successful start:

```bash
docker compose -f docker/docker-compose.yml --env-file .env logs openclaw-gateway -f
```

Look for both of these lines:

```
[telegram] starting provider (@careerclaw_orestes_bot)
[gateway] listening on ws://127.0.0.1:18789
```

Press `Ctrl+C` to stop following logs once the gateway is listening.

> The gateway is also accessible via the Control UI at
> http://localhost:18789

---

## Step 8 — Pair Your Telegram Account

Pairing links your Telegram account to the bot so only you can send
commands. The flow is inbound — you initiate from Telegram, then approve
via CLI.

**8a — Initiate from Telegram**

Open your bot in Telegram (e.g. `@careerclaw_orestes_bot`) and send any
message, e.g. `hi`. The bot will reply with a pairing code.

**8b — Approve via CLI**

```bash
# List pending pairing requests
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli pairing list

# Approve (replace CODE with the code the bot sent you)
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli pairing approve CODE
```

Expected output: `Approved telegram sender <your-id>.`

Send `hi` to the bot again — it should now respond as the OpenClaw agent.

---

## Step 9 — Configure Sandbox Environment Variables

The `CAREERCLAW_LLM_KEY` must be available inside the **sandbox
container** where `python -m careerclaw.briefing` runs — not just in
the gateway. Set it via the OpenClaw config CLI:

```bash
# Set the LLM key in the sandbox env config
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.sandbox.docker.env.CAREERCLAW_LLM_KEY "sk-ant-..."

# Set the custom sandbox image
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.sandbox.docker.image "careerclaw-sandbox:local"

# Enable sandbox mode
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config set agents.defaults.sandbox.mode "non-main"
```

Verify the config was saved:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm openclaw-cli \
  config get agents.defaults.sandbox
# Expected:
# {
#   "mode": "non-main",
#   "docker": {
#     "image": "careerclaw-sandbox:local",
#     "env": { "CAREERCLAW_LLM_KEY": "sk-ant-..." }
#   }
# }
```

Restart the gateway to apply:

```bash
docker compose -f docker/docker-compose.yml --env-file .env down
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

---

## Step 10 — Install CareerClaw and Run a Briefing

**Install the skill** — send this to your bot in Telegram:

```
install skill from https://github.com/orestes-garcia-martinez/careerclaw
```

**Dry-run briefing** (nothing saved to tracking):

```
Run a dry-run job briefing
```

**Real briefing** (saves to `.careerclaw/tracking.json`):

```
Run a job briefing
```

Expected output: top 3–5 job matches from RemoteOK and HN Who's Hiring,
with scores, fit percentages, draft email summaries, and an offer to
show the full email for any match.

---

## Quick Command Reference

All commands run from the CareerClaw repo root in WSL2.

| Command | What it does |
|---------|-------------|
| `docker compose ... up -d openclaw-gateway` | Start the gateway in the background |
| `docker compose ... down` | Stop and remove the gateway and network |
| `docker compose ... logs openclaw-gateway -f` | Stream gateway logs (Ctrl+C to stop) |
| `docker compose ... run --rm openclaw-cli <cmd>` | Run a one-off CLI command |
| `docker compose ... restart openclaw-gateway` | Restart the gateway after config changes |
| `docker build -f docker/Dockerfile.sandbox -t careerclaw-sandbox:local .` | Rebuild sandbox image after code changes |
| `docker images \| grep openclaw` | List all OpenClaw-related images |
| `docker ps \| grep openclaw` | List running OpenClaw containers |
| `docker volume rm careerclaw-openclaw-config` | Delete the named volume to reset gateway state |
| `docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data` | Fix volume permissions |

> Every `docker compose` command requires `-f docker/docker-compose.yml --env-file .env`.

---

## Isolation Contract

| Path | Access | Purpose |
|------|--------|---------|
| `.careerclaw/` | Read + Write | Profile, resume, tracking, run logs |
| `careerclaw/` source | None at runtime | Baked into the image at build time |
| `docker/` config files | None at runtime | Consumed by gateway only |
| Windows C: / D: drives | None | Docker bridge network, no host filesystem |
| Internet (RemoteOK, HN) | Allowed | Bridge network with outbound access |

---

## Troubleshooting

**`error getting credentials` on `docker run`**
Run `echo '{}' > ~/.docker/config.json` to remove the broken WSL2
credential helper. See Step 1.

**`EACCES: permission denied` in gateway logs**
Run the `alpine chown` command from Step 6, then restart the gateway.
If the volume is corrupted, delete it first:
```bash
docker compose -f docker/docker-compose.yml --env-file .env down
docker volume rm careerclaw-openclaw-config
docker run --rm -v careerclaw-openclaw-config:/data alpine chown -R 1000:1000 /data
docker compose -f docker/docker-compose.yml --env-file .env up -d openclaw-gateway
```

**Env vars show "variable is not set"**
Always use `--env-file .env` — Docker Compose looks for `.env` relative
to the compose file (`docker/`), not the repo root.

**Bot does not respond in Telegram**
Check that the gateway logs show `[telegram] starting provider`. If not,
`TELEGRAM_BOT_TOKEN` is missing or invalid. Check your `.env`.

**Agent says "No API key found for provider anthropic"**
Add `ANTHROPIC_API_KEY` to your `.env` and ensure it's in the gateway
environment in `docker-compose.yml`.

**CareerClaw drafts not LLM-enhanced**
The `CAREERCLAW_LLM_KEY` must be set inside the sandbox config via
`config set`, not just in `.env`. Run the `config set` commands from
Step 9 and restart the gateway.

**Sandbox container not starting / wrong image**
Verify `agents.defaults.sandbox.docker.image` is set to
`careerclaw-sandbox:local` via `config get agents.defaults.sandbox`.
If missing, run the `config set` command from Step 9.

**`careerclaw-sandbox:local` image not found**
Rebuild it: `docker build -f docker/Dockerfile.sandbox -t careerclaw-sandbox:local .`