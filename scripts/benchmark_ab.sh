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

if ! command -v hey &> /dev/null; then
  echo "Installing hey (load tester)..."
  go install github.com/rakyll/hey@latest
  export PATH="$PATH:$(go env GOPATH)/bin"
fi

for CONFIG in "${CONFIGS[@]}"; do
  echo "===== Starting server: VLLM_CONFIG=$CONFIG ====="
  VLLM_CONFIG="$CONFIG" nohup uvicorn app.app:app --host 0.0.0.0 --port 8000 \
    > "server_${CONFIG}.log" 2>&1 &
  SERVER_PID=$!

  echo "Waiting for model to load (this can take a few minutes)..."
  READY=0
  for i in $(seq 1 120); do
    if curl -sf http://localhost:8000/ | grep -q "\"vllm_config\":\"$CONFIG\""; then
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
    echo "===== [$CONFIG] Load testing: $REQUESTS requests, concurrency $CONCURRENCY ====="
    hey -n "$REQUESTS" -c "$CONCURRENCY" -m POST \
      -H "Content-Type: application/json" \
      -d "$PROMPT" \
      http://localhost:8000/generate > "results_${CONFIG}_c${CONCURRENCY}.txt"
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
