from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from vllm import LLM, SamplingParams
import time
import prometheus_client as prom

app = FastAPI(title="H100 Inference Control Plane")

REQUEST_COUNT = prom.Counter("requests_total", "Total inference requests")
ERRORS = prom.Counter("request_errors_total", "Total failed requests")

LATENCY = prom.Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    buckets=(0.1, 0.5, 1, 2, 5, 10)
)

INFLIGHT = prom.Gauge(
    "inflight_requests", "Requests currently being processed"
)

PROMPT_SIZE = prom.Histogram(
    "prompt_length_chars", "Prompt length in characters"
)

# TOP 3 ADDED METRICS:
PROMPT_TOKENS = prom.Histogram(
    "prompt_tokens", 
    "Actual token count of the input prompt",
    buckets=(10, 50, 100, 250, 500, 1000, 2000)
)

COMPLETION_TOKENS = prom.Histogram(
    "completion_tokens", 
    "Actual token count of the generated response",
    buckets=(10, 50, 100, 250, 512)
)

HTTP_REQUESTS = prom.Counter(
    "http_requests_total",
    "Total HTTP requests by method and status code",
    ["method", "status_code"]
)

# ELITE PERFORMANCE METRICS:
TTFT = prom.Histogram(
    "request_ttft_seconds",
    "Time to first token in seconds",
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

TPOT = prom.Histogram(
    "request_tpot_seconds",
    "Time per output token in seconds",
    buckets=(0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5)
)

TOKENS_PER_SECOND_GAUGE = prom.Gauge(
    "tokens_per_second_gauge",
    "Tokens generated per second (current request)"
)

TOKENS_PER_SECOND_HIST = prom.Histogram(
    "tokens_per_second_histogram",
    "Distribution of tokens generated per second",
    buckets=(5, 10, 20, 50, 100, 150, 200)
)

print("Loading Mistral-7B...")
llm = LLM(
    model="mistralai/Mistral-7B-Instruct-v0.1",
    tensor_parallel_size=1,
    dtype="float16",
    gpu_memory_utilization=0.90,
    max_model_len=4096
)

print("Model loaded")

@app.post("/generate")
async def generate(request: Request):
    INFLIGHT.inc()
    try:
        data = await request.json()
        prompt = data.get("prompt", "Hello, how are you?")

        PROMPT_SIZE.observe(len(prompt))
        REQUEST_COUNT.inc()

        start = time.time()

        sampling_params = SamplingParams(
            temperature=0.7,
            max_tokens=512
        )

        outputs = llm.generate(prompt, sampling_params)

        latency = time.time() - start
        LATENCY.observe(latency)

        generated_text = outputs[0].outputs[0].text

        # Observe accurate token metrics using vLLM token IDs
        prompt_tokens = len(outputs[0].prompt_token_ids)
        completion_tokens = len(outputs[0].outputs[0].token_ids)
        PROMPT_TOKENS.observe(prompt_tokens)
        COMPLETION_TOKENS.observe(completion_tokens)

        # Observe performance metrics (TTFT, TPOT, TPS) using vLLM RequestMetrics if available
        vllm_metrics = getattr(outputs[0], "metrics", None)
        ttft = None
        tpot = None
        tps = None

        if vllm_metrics is not None:
            if getattr(vllm_metrics, "first_token_time", None) and getattr(vllm_metrics, "arrival_time", None):
                ttft = vllm_metrics.first_token_time - vllm_metrics.arrival_time
                TTFT.observe(ttft)
            
            if (getattr(vllm_metrics, "finished_time", None) and 
                    getattr(vllm_metrics, "first_token_time", None) and 
                    completion_tokens > 0):
                tpot = (vllm_metrics.finished_time - vllm_metrics.first_token_time) / completion_tokens
                TPOT.observe(tpot)
                
            if getattr(vllm_metrics, "finished_time", None) and getattr(vllm_metrics, "arrival_time", None):
                total_duration = vllm_metrics.finished_time - vllm_metrics.arrival_time
                if total_duration > 0:
                    tps = completion_tokens / total_duration
                    TOKENS_PER_SECOND_GAUGE.set(tps)
                    TOKENS_PER_SECOND_HIST.observe(tps)

        # Do not fake TTFT/TPOT if vLLM RequestMetrics is unavailable.
        # Fall back only to total server-side generation throughput.
        if tps is None and latency > 0:
            tps = completion_tokens / latency
            TOKENS_PER_SECOND_GAUGE.set(tps)
            TOKENS_PER_SECOND_HIST.observe(tps)

        HTTP_REQUESTS.labels(method="POST", status_code="200").inc()

        return {
            "response": generated_text[:800],
            "latency_seconds": round(latency, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "ttft_seconds": round(ttft, 4) if ttft is not None else None,
            "tpot_seconds": round(tpot, 4) if tpot is not None else None,
            "tokens_per_second": round(tps, 2) if tps is not None else None
        }

    except Exception as e:
        ERRORS.inc()
        HTTP_REQUESTS.labels(method="POST", status_code="500").inc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    finally:
        INFLIGHT.dec()

@app.get("/metrics")
async def metrics():
    HTTP_REQUESTS.labels(method="GET", status_code="200").inc()
    return Response(
        prom.generate_latest(),
        media_type="text/plain"
    )

@app.get("/")
async def root():
    HTTP_REQUESTS.labels(method="GET", status_code="200").inc()
    return {"status": "ok"}


