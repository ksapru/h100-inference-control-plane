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

## avg prompt tokens (actual)
rate(prompt_tokens_sum[1m]) / rate(prompt_tokens_count[1m])

## avg completion tokens (actual)
rate(completion_tokens_sum[1m]) / rate(completion_tokens_count[1m])

## HTTP request error rate (non-200 / total)
sum(rate(http_requests_total{status_code!~"2.*"}[5m])) / sum(rate(http_requests_total[5m]))

## p90 Time to First Token (TTFT)
histogram_quantile(0.90, rate(request_ttft_seconds_bucket[1m]))

## p90 Time Per Output Token (TPOT)
histogram_quantile(0.90, rate(request_tpot_seconds_bucket[1m]))

## avg generation speed (Tokens Per Second)
rate(tokens_per_second_histogram_sum[1m]) / rate(tokens_per_second_histogram_count[1m])


