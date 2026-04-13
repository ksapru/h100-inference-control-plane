from fastapi import FastAPI, Request
from vllm import LLM, SamplingParams
import time
import prometheus_client as prom

app = FastAPI(title="H100 Inference Control Plane")

REQUEST_COUNT = prom.Counter('requests_total', 'Total inference requests')
LATENCY = prom.Histogram('request_latency_seconds', 'Request latency in seconds')

print("Loading Llama-3.2-1B...")
llm = LLM(
    model="mistralai/Mistral-7B-Instruct-v0.1",
    tensor_parallel_size=1,
    dtype="float16",
    gpu_memory_utilization=0.90,
    max_model_len=4096
)

@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "Hello, how are you?")
    
    start = time.time()
    REQUEST_COUNT.inc()
    
    sampling_params = SamplingParams(temperature=0.7, max_tokens=512)
    outputs = llm.generate(prompt, sampling_params)
    
    latency = time.time() - start
    LATENCY.observe(latency)
    
    return {
        "response": outputs[0].outputs[0].text[:800],
        "latency_seconds": round(latency, 3)
    }

@app.get("/metrics")
async def metrics():
    return prom.generate_latest()
