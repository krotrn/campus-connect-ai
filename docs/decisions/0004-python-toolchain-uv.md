# ADR 0004: Python Toolchain and Environment Management

## Status
Accepted

## Date
2026-09-02

## Context
Python 3.14 was present on the host system, but many core machine learning and scientific computing packages (PyTorch, ONNX Runtime, fastembed, tree-sitter bindings) do not yet publish prebuilt wheels for Python 3.14. Traditional package managers like standard `pip` or `poetry` can be slow to resolve complex dependency trees.

## Decision
We adopt **`uv`** as the package manager and environment manager, pinning Python version **3.12**.

Key characteristics:
- Deterministic lockfile (`uv.lock`) ensuring identical environments across local machines and Docker containers.
- Sub-second package installation and dependency resolution.
- Native Python version management (`uv python install 3.12`).

## Consequences
- **Positive**: Blazing fast dependency resolution; full wheel compatibility with ONNX Runtime, FastEmbed, and Qdrant client.
- **Positive**: Simplified Docker builds leveraging `uv`'s cache and multi-stage build patterns.

