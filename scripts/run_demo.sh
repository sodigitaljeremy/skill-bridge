#!/usr/bin/env bash
# Lance API FastAPI + Streamlit ensemble. Ctrl-C arrête les deux proprement.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_URL="${SKILLBRIDGE_API_URL:-http://localhost:8000}"

cleanup() {
  echo ""
  echo "Arrêt des processus..."
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "${FRONT_PID:-}" ] && kill "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ Démarrage API sur $API_URL"
uv run uvicorn skill_bridge.adapters.inbound.api.app:create_app \
  --factory --port 8000 > /tmp/skill-bridge-api.log 2>&1 &
API_PID=$!

echo "  PID $API_PID — logs: /tmp/skill-bridge-api.log"
echo "  Attente du démarrage..."
for _ in $(seq 1 90); do
  if curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo "  API prête."
    break
  fi
  sleep 1
done

if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
  echo "  L'API n'a pas répondu après 90 s. Voir /tmp/skill-bridge-api.log"
  exit 1
fi

echo ""
echo "→ Démarrage Streamlit sur http://localhost:8501"
# --server.headless=true : pas de prompt interactif (email) au 1er lancement, pas
# d'ouverture auto du navigateur. L'app reste accessible sur localhost:8501.
uv run streamlit run src/skill_bridge/adapters/inbound/streamlit_app.py \
  --server.headless=true --server.port=8501 --browser.gatherUsageStats=false &
FRONT_PID=$!

wait $FRONT_PID
