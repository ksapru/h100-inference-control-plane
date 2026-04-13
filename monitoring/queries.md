# VictoriaMetrics Queries

## QPS
rate(requests_total[1m])

## p50 latency
histogram_quantile(0.5, rate(request_latency_seconds_bucket[1m]))

## p95 latency
histogram_quantile(0.95, rate(request_latency_seconds_bucket[1m]))

## p99 latency
histogram_quantile(0.99, rate(request_latency_seconds_bucket[1m]))

## inflight requests
inflight_requests

## avg tokens per request
rate(generated_tokens_sum[1m]) / rate(generated_tokens_count[1m])
