#!/bin/bash
# update.sh
#
# Updates CareerClaw locally after pushing changes to GitHub.
# Run from the CareerClaw repo root in WSL2.
#
# Usage:
#   ./update.sh           — update everything (skill.md + rebuild image)
#   ./update.sh --skill   — update SKILL.md only (no image rebuild)
#   ./update.sh --code    — rebuild sandbox image only (no SKILL.md update)

set -e

COMPOSE="docker compose -f docker/docker-compose.yml --env-file .env"
SKILL_RAW="https://raw.githubusercontent.com/orestes-garcia-martinez/careerclaw/main/SKILL.md"
SANDBOX_IMAGE="careerclaw-sandbox:local"

# ── Parse args ───────────────────────────────────────────────────────────────
UPDATE_SKILL=true
UPDATE_CODE=true

if [[ "$1" == "--skill" ]]; then
  UPDATE_CODE=false
elif [[ "$1" == "--code" ]]; then
  UPDATE_SKILL=false
fi

echo ""
echo "🦞 CareerClaw — Local Update"
echo "────────────────────────────────────────"

# ── Step 1: Rebuild sandbox image (if code changed) ──────────────────────────
if [[ "$UPDATE_CODE" == true ]]; then
  echo ""
  echo "▶  Rebuilding sandbox image (Python source changes)..."
  docker build -f docker/Dockerfile.sandbox -t $SANDBOX_IMAGE . --quiet
  echo "✔  careerclaw-sandbox:local rebuilt."
fi

# ── Step 2: Restart gateway ───────────────────────────────────────────────────
if [[ "$UPDATE_CODE" == true ]]; then
  echo ""
  echo "▶  Restarting gateway to pick up new sandbox image..."
  $COMPOSE down 2>&1 | tail -1
  $COMPOSE up -d openclaw-gateway 2>&1 | tail -1
  echo "✔  Gateway restarted."

  # Give the gateway a moment to fully start before the SKILL.md update
  sleep 3
fi

# ── Step 3: Update SKILL.md via raw URL ───────────────────────────────────────
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