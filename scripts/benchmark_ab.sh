#!/bin/bash
# Runs the actual default-vs-optimized A/B comparison the README's table claims,
# and commits the raw evidence instead of leaving the numbers unverifiable.
#
# For each config in CONFIGS: starts the server once with VLLM_CONFIG=<config>,
# waits for the model to finish loading, then load-tests it at EVERY concurrency
# in CONCURRENCIES (both configs hit the same concurrency levels, so the
# comparison isolates the config change instead of also varying load). Saves
# each run's raw `hey` output to results_<config>_c<concurrency>.txt, then
# stops the server before moving to the next config (both configs load the
# same model, so they can't run concurrently on one GPU).
set -euo pipefail
cd "$(dirname "$0")/.."

REQUESTS="${REQUESTS:-1000}"
CONCURRENCIES=(${CONCURRENCIES:-16 32 64})
PROMPT='{"prompt":"Explain GPUs simply"}'
CONFIGS=(default optimized)
# 8000 is claimed by this platform's own reverse proxy (Caddy) on Vast.ai's
# base image, not free for our app to bind -- use PORT to pick a free one.
PORT="${PORT:-9001}"
# Safety net: a stuck/runaway sweep burns real GPU-rental money. Bound each
# one so a hang fails fast instead of running for however long the caller
# forgets about it. Bump this if REQUESTS/CONCURRENCIES are scaled up.
SWEEP_TIMEOUT="${SWEEP_TIMEOUT:-300}"

# hey's official binary host (hey-release.s3.us-east-2.amazonaws.com) resolves
# outside AWS's published ranges -- looks hijacked/dangling, so we don't fetch
# a binary from it. scripts/load_test.py does the same job from source instead.
python3 -c "import aiohttp" 2>/dev/null || pip install -q aiohttp

for CONFIG in "${CONFIGS[@]}"; do
  echo "===== Starting server: VLLM_CONFIG=$CONFIG ====="
  VLLM_CONFIG="$CONFIG" nohup uvicorn app.app:app --host 0.0.0.0 --port "$PORT" \
    > "server_${CONFIG}.log" 2>&1 &
  SERVER_PID=$!

  echo "Waiting for model to load (this can take a few minutes)..."
  READY=0
  for i in $(seq 1 120); do
    if curl -sf http://localhost:$PORT/ | grep -q "\"vllm_config\":\"$CONFIG\""; then
      echo "Server ready after ${i}0s."
      READY=1
      break
    fi
    sleep 10
  done
  if [ "$READY" -ne 1 ]; then
    echo "Server did not become ready in time; see server_${CONFIG}.log" >&2
    kill "$SERVER_PID" 2>/dev/null || true
    exit 1
  fi

  for CONCURRENCY in "${CONCURRENCIES[@]}"; do
    echo "===== [$CONFIG] Load testing: $REQUESTS requests, concurrency $CONCURRENCY (timeout ${SWEEP_TIMEOUT}s) ====="
    if ! timeout "$SWEEP_TIMEOUT" python3 scripts/load_test.py -n "$REQUESTS" -c "$CONCURRENCY" \
      -d "$PROMPT" \
      http://localhost:$PORT/generate > "results_${CONFIG}_c${CONCURRENCY}.txt"; then
      echo "Sweep exceeded ${SWEEP_TIMEOUT}s or failed; aborting to avoid burning more GPU time." >&2
      echo "Partial output (if any) is in results_${CONFIG}_c${CONCURRENCY}.txt" >&2
      kill "$SERVER_PID" 2>/dev/null || true
      exit 1
    fi
    echo "Saved results_${CONFIG}_c${CONCURRENCY}.txt"
  done

  echo "===== Stopping server ====="
  kill "$SERVER_PID"
  wait "$SERVER_PID" 2>/dev/null || true
  sleep 5
done

echo ""
echo "===== DONE ====="
echo "Raw evidence saved (commit these):"
for CONFIG in "${CONFIGS[@]}"; do
  for CONCURRENCY in "${CONCURRENCIES[@]}"; do
    echo " - results_${CONFIG}_c${CONCURRENCY}.txt"
  done
  echo " - server_${CONFIG}.log"
done
