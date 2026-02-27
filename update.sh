#!/bin/bash
# update.sh
#
# Updates CareerClaw locally after pushing changes to GitHub.
# Run from the CareerClaw repo root in WSL2.
#
# Usage:
#   ./update.sh           — update everything (skill.md + rebuild sandbox image)
#   ./update.sh --skill   — update SKILL.md only (no image rebuild, no repo pull)
#   ./update.sh --code    — rebuild sandbox image only (for ClawHub deployment artifact)
#   ./update.sh --repo    — pull latest code into gateway's cloned repo (local testing)
#
# ── Which flag should I use? ────────────────────────────────────────────────
#
#   Local testing (gateway runs from cloned repo):
#     1. git push your changes to GitHub
#     2. ./update.sh --repo       ← pulls latest code into the gateway's repo clone
#     3. ./update.sh --skill      ← if SKILL.md also changed
#
#   ClawHub deployment (sandbox image is the artifact):
#     1. git push your changes to GitHub
#     2. ./update.sh --code       ← rebuilds openclaw-sandbox:careerclaw image
#     3. ./update.sh --skill      ← if SKILL.md also changed

set -e

COMPOSE="docker compose -f docker/docker-compose.yml --env-file .env"
SKILL_RAW="https://raw.githubusercontent.com/orestes-garcia-martinez/careerclaw/main/SKILL.md"
SANDBOX_IMAGE="openclaw-sandbox:careerclaw"
GATEWAY_REPO="/home/node/.openclaw/workspace/.careerclaw-repo"

# ── Parse args ───────────────────────────────────────────────────────────────
UPDATE_SKILL=true
UPDATE_CODE=true
UPDATE_REPO=false

if [[ "$1" == "--skill" ]]; then
  UPDATE_CODE=false
  UPDATE_REPO=false
elif [[ "$1" == "--code" ]]; then
  UPDATE_SKILL=false
  UPDATE_REPO=false
elif [[ "$1" == "--repo" ]]; then
  UPDATE_CODE=false
  UPDATE_SKILL=false
  UPDATE_REPO=true
fi

echo ""
echo "🦞 CareerClaw — Local Update"
echo "────────────────────────────────────────"

# ── Step 1: Pull latest code into gateway's cloned repo (local testing) ──────
if [[ "$UPDATE_REPO" == true ]]; then
  echo ""
  echo "▶  Pulling latest code into gateway repo clone (local testing)..."
  $COMPOSE exec openclaw-gateway sh -c "cd $GATEWAY_REPO && git pull origin main" 2>&1
  echo "✔  Gateway repo updated. Changes are live immediately — no restart needed."
fi

# ── Step 2: Rebuild sandbox image (ClawHub deployment artifact) ───────────────
if [[ "$UPDATE_CODE" == true ]]; then
  echo ""
  echo "▶  Rebuilding sandbox image (ClawHub deployment artifact)..."
  docker build -f docker/Dockerfile.sandbox -t $SANDBOX_IMAGE . --quiet
  echo "✔  $SANDBOX_IMAGE rebuilt."
fi

# ── Step 3: Restart gateway (only needed after sandbox image rebuild) ─────────
if [[ "$UPDATE_CODE" == true ]]; then
  echo ""
  echo "▶  Restarting gateway to pick up new sandbox image..."
  $COMPOSE down 2>&1 | tail -1
  $COMPOSE up -d openclaw-gateway 2>&1 | tail -1
  echo "✔  Gateway restarted."

  # Give the gateway a moment to fully start before the SKILL.md update
  sleep 3
fi

# ── Step 4: Update SKILL.md via raw URL ───────────────────────────────────────
if [[ "$UPDATE_SKILL" == true ]]; then
  echo ""
  echo "▶  Fetching latest SKILL.md from GitHub..."
  HTTP_STATUS=$(curl -s -o /tmp/careerclaw_skill.md -w "%{http_code}" "$SKILL_RAW")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    echo "✔  SKILL.md fetched successfully."
    echo ""
    echo "────────────────────────────────────────"
    echo "📨  Now send this message to your Telegram bot:"
    echo ""
    echo "  Update the careerclaw skill. Fetch the new SKILL.md from"
    echo "  $SKILL_RAW"
    echo "  and replace the current skill definition."
    echo ""
    echo "────────────────────────────────────────"
  else
    echo "✖  Failed to fetch SKILL.md (HTTP $HTTP_STATUS). Check your internet connection."
    exit 1
  fi
fi

echo ""
echo "✔  Done."
echo ""
