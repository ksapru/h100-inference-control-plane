#!/bin/bash

echo "Starting VictoriaMetrics..."

if [ ! -f victoria-metrics ]; then
  wget https://github.com/VictoriaMetrics/VictoriaMetrics/releases/latest/download/victoria-metrics-linux-amd64 -O victoria-metrics
  chmod +x victoria-metrics
fi

./victoria-metrics
