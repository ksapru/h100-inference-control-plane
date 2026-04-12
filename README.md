# h100-inference-control-plane

**Production-grade Kubernetes GPU Inference Platform** built on H100 GPUs.

A clean, observable, and scalable inference stack designed for learning modern AI inference infrastructure.

## Overview

This repository contains a complete, real-world-style inference platform using:
- **Kubernetes** (k3s) + **NVIDIA GPU Operator**
- **vLLM** as the high-performance inference engine (with continuous batching + PagedAttention)
- **VictoriaMetrics** + **Grafana** for observability
- Targeted at **4x or 8x H100** nodes

## Goals

- Learn modern GPU inference infrastructure patterns used by hyperscalers and AI companies
- Practice Kubernetes-native GPU workloads
- Build production-like observability for inference services
- Understand continuous batching, KV cache management, and cost/performance tradeoffs

## Tech Stack

- **Orchestration**: Kubernetes (k3s) + NVIDIA GPU Operator
- **Inference Engine**: vLLM (with tensor parallelism)
- **API Layer**: FastAPI
- **Monitoring**: VictoriaMetrics + Prometheus + Grafana
- **Hardware Target**: NVIDIA H100 SXM

## Features

- Multi-GPU inference with tensor parallelism
- Continuous / dynamic batching
- Real-time metrics (TTFT, TPOT, throughput, tokens/sec, GPU utilization, queue depth)
- Cost per token tracking
- Easy one-command deploy and teardown

## Repository Structure
