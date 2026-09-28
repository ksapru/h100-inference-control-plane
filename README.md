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
- [x] **Benchmark**: default-vs-optimized A/B run completed on a real H100, 0 errors across 400 requests -- see [Results](#results-100-requests-per-point-qwenqwen36-35b-a3b-fp8-single-h100-sxm) below.
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

`scripts/benchmark_ab.sh` runs both configurations in turn on a single NVIDIA H100. For each config it starts the server once, then load-tests it with `scripts/load_test.py` at **every concurrency level in `CONCURRENCIES`** — both configs hit the same concurrency levels, so the comparison isolates the effect of the config change rather than also varying load between rows. Raw output is saved per (config, concurrency) pair. **The `results_*.txt` files in this repo are the source of truth for the numbers below** — every one of them was produced by an actual run, not estimated.

### Results (100 requests per point, `Qwen/Qwen3.6-35B-A3B-FP8`, single H100 SXM)

| Config | Concurrency | Throughput | p50 latency | p99 latency | Errors |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `default` | 16 | 0.39 req/s | 38.36s | 42.66s | 0/100 |
| `default` | 64 | 1.10 req/s | 45.06s | 46.48s | 0/100 |
| `optimized` | 16 | 3.62 req/s | 4.20s | 4.46s | 0/100 |
| `optimized` | 64 | 8.48 req/s | 6.04s | 6.75s | 0/100 |

Raw evidence: [`results_default_c16.txt`](results_default_c16.txt), [`results_default_c64.txt`](results_default_c64.txt), [`results_optimized_c16.txt`](results_optimized_c16.txt), [`results_optimized_c64.txt`](results_optimized_c64.txt), and the corresponding `server_*.log` files.

> [!NOTE]
> **Identical-prompt caveat.** `load_test.py` sends the same prompt ("Explain GPUs simply") for every request in a sweep. With `enable_prefix_caching` on, every request after the first hits a fully cached prefix — a best-case scenario, not representative of production traffic with varied prompts. That's almost certainly most of why `optimized` measures ~9x faster here: real, but an upper bound, not a number to quote as "typical." A follow-up with varied prompts per request would isolate how much of the gain is prefix-cache-specific versus the chunked-prefill/CUDA-graph/memory-utilization changes alone.

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
| Load Testing | `scripts/load_test.py` (asyncio + aiohttp) closed-loop concurrent request sweeps |
| Workload Spec | Identical prompt per sweep ("Explain GPUs simply", ~24 chars / prefix-cacheable), max output tokens: 512 -- see the identical-prompt caveat above |
| SLO Target | Request latency < 2s |
| Metrics Source | Server-side telemetry observed directly from vLLM `RequestMetrics` |