#!/bin/bash
set -e

echo "===== STEP 1: Setup ====="

sudo apt update -y
sudo apt install -y python3-pip wget

echo "===== STEP 2: Clone repo ====="

git clone https://github.com/ksapru/h100-inference-control-plane.git
cd h100-inference-control-plane

echo "===== STEP 3: Install Python deps ====="

pip install -r requirements.txt

echo "===== STEP 4: Start inference server ====="

nohup uvicorn app.app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &

sleep 5

echo "===== STEP 5: Verify server ====="

curl http://localhost:8000/metrics || echo "Server not ready yet"

echo "===== STEP 6: Start VictoriaMetrics ====="

wget https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/v1.93.3/victoria-metrics-linux-amd64 -O vm
chmod +x vm

nohup ./vm -retentionPeriod=1 > vm.log 2>&1 &

sleep 3

echo "===== STEP 7: Start metrics ingestion loop ====="

nohup bash -c '
while true; do
  curl -s http://localhost:8000/metrics | \
  curl -s -X POST --data-binary @- http://localhost:8428/api/v1/import/prometheus
  sleep 2
done
' > ingest.log 2>&1 &

echo "===== STEP 8: Install load tester ====="

go install github.com/rakyll/hey@latest
export PATH=$PATH:$(go env GOPATH)/bin

sleep 2

echo "===== STEP 9: Run load test ====="

hey -n 1000 -c 64 -m POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain GPUs simply"}' \
  http://localhost:8000/generate > results.txt

echo "===== STEP 10: Query metrics ====="

curl "http://localhost:8428/api/v1/query?query=requests_total" > vm_query.txt

echo "===== DONE ====="
echo "Saved:"
echo " - results.txt"
echo " - vm_query.txt"
echo " - server.log"
echo " - vm.log"
echo " - ingest.log"
