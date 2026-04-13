#!/bin/bash

echo "Pushing metrics to VictoriaMetrics..."

while true; do
  curl -s http://localhost:8000/metrics | \
  curl -s -X POST --data-binary @- http://localhost:8428/api/v1/import/prometheus
  sleep 2
done
