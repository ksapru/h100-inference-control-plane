from fastapi import FastAPI, Request
from fastapi.responses import Response
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

TOKENS = prom.Histogram(
    "generated_tokens", "Generated token count"
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
        token_count = len(generated_text.split())
        TOKENS.observe(token_count)

        return {
            "response": generated_text[:800],
            "latency_seconds": round(latency, 3),
            "tokens": token_count
        }

    except Exception as e:
        ERRORS.inc()
        return {"error": str(e)}

    finally:
        INFLIGHT.dec()

@app.get("/metrics")
async def metrics():
    return Response(
        prom.generate_latest(),
        media_type="text/plain"
    )

@app.get("/")
async def root():
    return {"status": "ok"}
