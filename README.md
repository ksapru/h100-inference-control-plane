# h100-inference-control-plane

**H100-targeted async LLM inference control plane** for FP8 model serving, observability, SLO analysis, and load testing.

This repository provides a production-style inference stack for scaling modern LLM workloads using **vLLM AsyncLLMEngine**, **FastAPI**, **VictoriaMetrics**, and **Grafana**. The platform is benchmarked with `Qwen/Qwen3.6-35B-A3B-FP8` and focuses on production-critical metrics including **TTFT**, **TPOT**, **tokens/sec**, **p95/p99 latency**, **prompt/completion tokens**, **inflight requests**, **HTTP error rates**, and **SLO violations**.

## Current Status: Functional Core

- [x] **Inference Engine**: Async vLLM integration with `Qwen/Qwen3.6-35B-A3B-FP8`.
- [x] **API Layer**: FastAPI async inference API using vLLM `AsyncLLMEngine`.
- [x] **FP8 Serving**: FP8-quantized model backend optimized for H100-class GPU serving.
- [x] **Observability**: Prometheus-compatible metrics for TTFT, TPOT, latency, token throughput, prompt tokens, completion tokens, inflight requests, HTTP status codes, and SLO violations.
- [x] **Monitoring**: VictoriaMetrics + Grafana dashboard support.
- [x] **Automation**: One-command local deployment and load testing.
- [ ] **Kubernetes**: Helm-based monitoring setup in progress; manifests not yet written (`kubernetes/` is currently a placeholder).
- [ ] **Grafana dashboards**: not yet built (`monitoring/dashboards/` is currently a placeholder).

## Default vs. Optimized vLLM Configurations

`app/app.py` reads `VLLM_CONFIG` (`default` or `optimized`) and serves `Qwen/Qwen3.6-35B-A3B-FP8` with a different set of `AsyncEngineArgs` accordingly:

| | `default` | `optimized` |
| :--- | :---: | :---: |
| `gpu_memory_utilization` | 0.85 | 0.90 |
| `enable_chunked_prefill` | off | on |
| `enable_prefix_caching` | off | on |
| CUDA graphs (`enforce_eager`) | off (eager) | on |

`scripts/benchmark_ab.sh` runs both configurations in turn on a single NVIDIA H100. For each config it starts the server once, then load-tests it with `hey` at **every concurrency level in `CONCURRENCIES` (default: 16, 32, 64)** — both configs hit the same concurrency levels, so the comparison isolates the effect of the config change rather than also varying load between rows. Raw output is saved per (config, concurrency) pair, e.g. `results_default_c16.txt`, `results_optimized_c64.txt`. **Those files are the source of truth for any numbers in this README.**

> [!NOTE]
> Not yet run. The specific throughput/latency numbers previously in this section, and the mismatched concurrency levels (16 for one row, 64 for the other) they were shown at, were not backed by a run this repo could reproduce — the code only ever supported one hardcoded config, and the load test script only ever ran once, at concurrency 64. Both gaps are now fixed (the `VLLM_CONFIG` toggle above, and the concurrency sweep in `benchmark_ab.sh`); this section stays a placeholder until the script has actually been run and its `results_*.txt` output committed.

---

## Metrics & Observability

The platform exports Prometheus-compatible metrics for LLM serving performance, token-level behavior, and reliability analysis.

### Request-Level Metrics

- `requests_total`: Total inference requests.
- `request_errors_total`: Total failed inference requests.
- `http_requests_total{method,status_code}`: HTTP request volume by method and status code (specifically mapping 500s on exception catches).
- `inflight_requests`: Number of requests currently being processed.
- `request_latency_seconds`: Server-side request latency measured inside the FastAPI handler.

### Token-Level Metrics

- `prompt_length_chars`: Prompt length distribution in characters.
- `prompt_tokens`: Actual input token count extracted directly from vLLM token IDs.
- `completion_tokens`: Actual generated token count extracted directly from vLLM token IDs.

### LLM Performance Metrics

- `request_ttft_seconds`: Server-side Time to First Token (TTFT) using vLLM request timing metadata.
- `request_tpot_seconds`: Server-side Time per Output Token (TPOT) using vLLM request timing metadata.
- `tokens_per_second_gauge`: Latest observed generated-token throughput.
- `tokens_per_second_histogram`: Distribution of generated-token throughput.

### SLO Metrics

The benchmark uses the following latency SLO:
```text
request latency < 2s
```
SLO violations are tracked as the percentage of requests exceeding the latency threshold during load testing.

---

## Benchmark Setup

| Field | Value |
|---|---|
| Model | `Qwen/Qwen3.6-35B-A3B-FP8` (35B parameters, 3B active per token) |
| Serving Engine | vLLM `AsyncLLMEngine` (vllm >= 0.6.0) |
| Quantization | FP8 (native Hopper Transformer Engine execution) |
| Hardware | NVIDIA H100 SXM (80GB HBM3) |
| API Layer | FastAPI (Asynchronous Gateway) |
| Monitoring | VictoriaMetrics + Grafana |
| Load Testing | `hey` closed-loop concurrent request sweeps (identical payloads with prefix caching enabled) |
| Workload Spec | Mixed prompts (avg. input length: 60 tokens / 256 chars, max output tokens: 512) |
| SLO Target | Request latency < 2s |
| Metrics Source | Server-side telemetry observed directly from vLLM `RequestMetrics` |