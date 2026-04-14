#!/bin/bash
set -e

echo "Deploying H100 Inference Control Plane"

# Install dependencies if needed
if ! command -v helm &> /dev/null; then
    echo "Installing Helm"
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# Add repos
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo add victoriametrics https://victoriametrics.github.io/helm-charts/
helm repo add grafana https://grafana.github.io/helm-charts/
helm repo update

echo "Installing VictoriaMetrics"
helm install vm victoriametrics/victoria-metrics-single --namespace monitoring --create-namespace

echo "Installing Grafana"
helm install grafana grafana/grafana --namespace monitoring --create-namespace

echo "Deploying vLLM inference service"
kubectl apply -f kubernetes/base/

echo "Deployment completed"
echo "Run ./scripts/monitor.sh to see monitoring"
