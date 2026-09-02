# ADR 0006: Local Ingestion Embedding Execution: CPU vs. GPU Trade-Off

## Status
Accepted

## Date
2026-09-03

## Context
We evaluated utilizing the host's NVIDIA GeForce RTX 3050 Laptop GPU via `onnxruntime-gpu` for local embeddings versus running on the multi-core CPU via standard `onnxruntime`.

Running `onnxruntime-gpu` requires:
1. Compiled CUDA Toolkit runtime libraries (`libcublasLt.so`, `cudnn`).
2. Downloading ~1.3 GB of deep learning runtime wheels (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`) or configuring dynamic linker search paths (`LD_LIBRARY_PATH`) on Linux.
3. Managing version coupling between PyPI ONNX wheels and system driver versions.

Conversely, benchmarking standard `fastembed` with `BAAI/bge-small-en-v1.5` on the CPU demonstrated:
- **Throughput**: ~13 milliseconds per chunk (10 chunks in 0.136s).
- **Total Ingestion Time**: ~60 seconds to index the entire 4,865-chunk repository.
- **Dependency Footprint**: Lightweight (~67 MB model weights), zero external CUDA dependencies, 100% reproducible across any machine, container, or CI/CD runner.

## Decision
We select **CPU execution** via standard `onnxruntime` and `fastembed` for the ingestion pipeline.

## Consequences
- **Positive**: Zero extra GPU driver or CUDA library dependencies; completely portable across local dev, Docker containers, and CI/CD pipelines.
- **Positive**: Total corpus ingestion takes under 60 seconds, which is fast enough for one-off and incremental updates.
- **Positive**: Avoids multi-gigabyte wheel downloads and platform-specific `.so` linking issues.

