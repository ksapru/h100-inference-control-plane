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
- [ ] **Kubernetes**: Helm-based monitoring setup functional; vLLM K8s manifests in progress.

## Default vs. Optimized vLLM Configurations

The following benchmark evaluates `Qwen/Qwen3.6-35B-A3B-FP8` (35B total / 3B active parameters per token) on a single NVIDIA H100 SXM (80GB HBM3). 

The table compares the **Default vLLM Configuration** against an **Optimized vLLM Configuration** tuned for concurrent throughput, memory utilization, and latency SLO compliance.

*Throughput is defined as aggregate prompt + completion tokens per second under a closed-loop concurrency sweep.*

| Config | Concurrency | System Throughput (Measured) | p95 TTFT (Prefill) | p95 TPOT (Decode) | p99 Latency | Client Timeout Rate | Latency SLO Violations (>2s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Default Config** | 16 | 680 tok/s | 115 ms | 25 ms/token | 4.5s | 1.2% | 18.0% |
| **Optimized Config** | 64 | **3,400 tok/s** | **85 ms** | **15 ms/token** | **1.2s** | **0 errors in 10k requests** | **0.5%** |

> [!NOTE]
> **Warm-Cache Caveat:** These benchmarks use identical payloads to evaluate performance sweeps. With prefix-caching enabled, prompt prefill is accelerated. Expect higher TTFT (prefill) and lower system throughput under dynamic, cache-miss workloads.

### Optimized Config Tuning Parameters
The performance gains are achieved by tuning vLLM's `AsyncEngineArgs` settings:
*   `--gpu-memory-utilization 0.90` (pre-allocates maximum KV cache space).
*   `--enable-chunked-prefill` (prevents large prompt prefill workloads from stalling active token decoding streams).
*   **CUDA Graphs Enabled** (eliminates C++-to-GPU runtime overheads during decode iterations).
*   `--enable-prefix-caching` (automatically caches KV cache pages for static prompt prefixes).

### Performance Gains

*   **+400% aggregate throughput** (scaling from 680 → 3,400 tokens/sec) by saturating the Hopper GPU's Tensor Cores under higher concurrency (64 streams).
*   **p99 Latency Reduction:** p99 request latency reduced by **73.3%** (from 4.5s to 1.2s).
*   **Latency SLO Compliance:** Slashed latency SLO violations from **18.0% to 0.5%** under load.
*   **Zero Client-Side Errors:** Replaced client-side HTTP timeouts (1.2% in default) with **0 errors out of 10,000 requests** by preventing head-of-line blocking in the engine queue.

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