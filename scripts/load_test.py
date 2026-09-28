#!/usr/bin/env python3
"""Minimal async load tester, standing in for `hey`.

`hey`'s official download host (hey-release.s3.us-east-2.amazonaws.com)
resolves to an address outside AWS's published ranges, not the real S3
endpoint's IPs -- looks like a dangling/hijacked DNS record, so we don't
fetch a prebuilt binary from it. This script does the same job (fire N
requests at C concurrency against a URL, report latency percentiles and
error rate) using only the stdlib and aiohttp (from PyPI).

Output is intentionally similar in spirit to hey's summary, so it can drop
into benchmark_ab.sh's results_<config>_c<concurrency>.txt files.
"""
import argparse
import asyncio
import json
import time

import aiohttp


async def worker(session, url, payload, results, sem):
    async with sem:
        start = time.monotonic()
        try:
            async with session.post(url, json=payload) as resp:
                await resp.read()
                results.append((time.monotonic() - start, resp.status, None))
        except Exception as e:  # noqa: BLE001 -- record any failure, keep going
            results.append((time.monotonic() - start, None, str(e)))


async def run(url, payload, n, concurrency):
    sem = asyncio.Semaphore(concurrency)
    results = []
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        start = time.monotonic()
        await asyncio.gather(*(worker(session, url, payload, results, sem) for _ in range(n)))
        wall = time.monotonic() - start
    return results, wall


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, required=True, help="total requests")
    ap.add_argument("-c", type=int, required=True, help="concurrency")
    ap.add_argument("-d", required=True, help="JSON request body")
    ap.add_argument("url")
    args = ap.parse_args()

    payload = json.loads(args.d)
    results, wall = asyncio.run(run(args.url, payload, args.n, args.c))

    latencies = sorted(r[0] for r in results)
    ok = [r for r in results if r[1] == 200]
    errors = [r for r in results if r[1] != 200]

    print("Load test summary")
    print("------------------")
    print(f"  Requests:            {args.n}")
    print(f"  Concurrency:         {args.c}")
    print(f"  Total time:          {wall:.3f} secs")
    print(f"  Requests/sec:        {args.n / wall:.4f}")
    print()
    print(f"  Successful (200):    {len(ok)}")
    print(f"  Errors:              {len(errors)}")
    print(f"  Error rate:          {100 * len(errors) / args.n:.2f}%")
    for _, status, err in errors[:5]:
        print(f"    example error: status={status} err={err}")
    print()
    print("Latency distribution (seconds):")
    for p in (0.50, 0.90, 0.95, 0.99):
        print(f"  {int(p*100)}% in {percentile(latencies, p):.4f} secs")
    print(f"  min in {latencies[0] if latencies else float('nan'):.4f} secs")
    print(f"  max in {latencies[-1] if latencies else float('nan'):.4f} secs")


if __name__ == "__main__":
    main()
