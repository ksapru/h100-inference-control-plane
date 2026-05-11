# h100-inference-control-plane

**Production-grade Kubernetes GPU Inference Platform** built on NVIDIA H100 GPUs.

This repository provides a high-performance inference stack designed for scaling modern AI workloads, featuring vLLM, VictoriaMetrics, and automated deployment pipelines.

## Current Status: Functional Core
The platform currently features a fully functional **FastAPI + vLLM** inference core with integrated observability.

- [x] **Inference Engine**: vLLM integration with Mistral-7B-Instruct.
- [x] **API Layer**: FastAPI with asynchronous request handling.
- [x] **Observability**: Custom Prometheus metrics (TTFT, Latency, Throughput, Token Counts).
- [x] **Automation**: End-to-end "one-command" local deployment and load testing.
- [ ] **Kubernetes**: Helm-based monitoring setup (Functional); vLLM K8s manifests (In Progress).

## Tech Stack

- **Inference Engine**: [vLLM](https://github.com/vllm-project/vllm) (PagedAttention + Continuous Batching)
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Monitoring**: [VictoriaMetrics](https://victoriametrics.com/) (Prometheus-compatible)
- **Visualization**: [Grafana](https://grafana.com/)
- **Load Testing**: [hey](https://github.com/rakyll/hey)
- **Hardware Target**: NVIDIA H100 SXM

## Repository Structure

```bash
h100-inference-control-plane/
├── app/                 # FastAPI application (vLLM integration)
│   └── app.py           # Core inference logic & Prometheus metrics
├── scripts/             # Deployment & automation scripts
│   ├── run_all.sh       # Automated local E2E setup & load test
│   └── deploy.sh        # Kubernetes/Helm deployment script
├── monitoring/          # Observability configuration
│   ├── push_metrics.sh  # Sidecar script for metrics ingestion
│   ├── queries.md       # Pre-built PromQL queries for dashboards
│   └── run_victoria.sh  # Local VictoriaMetrics runner
├── kubernetes/          # K8s manifests (Base & Overlays)
├── configs/             # Model and system configurations
└── docs/                # Architecture diagrams & technical notes
```

## Quick Start (Local Demo)

The fastest way to see the platform in action is using the automated setup script. This script clones the environment, installs dependencies, starts the inference server, and runs a load test.

```bash
# Run the full end-to-end automated demo
./scripts/run_all.sh
```

### Manual Components

If you prefer to run components individually:

1. **Start the Inference Server**:
   ```bash
   uvicorn app.app:app --host 0.0.0.0 --port 8000
   ```

2. **Launch VictoriaMetrics**:
   ```bash
   ./monitoring/run_victoria.sh
   ```

3. **Start Metrics Ingestion**:
   ```bash
   ./monitoring/push_metrics.sh
   ```

## Metrics & Observability

The platform exports detailed metrics for monitoring LLM performance:

- `requests_total`: Total inference requests.
- `request_latency_seconds`: Histogram of end-to-end request latency.
- `inflight_requests`: Number of requests currently being processed.
- `generated_tokens`: Histogram of tokens generated per request.
- `prompt_length_chars`: Distribution of input prompt sizes.

Useful queries can be found in [monitoring/queries.md](monitoring/queries.md).


*Note: Ensure you have a functional Kubernetes cluster with the NVIDIA GPU Operator installed.*