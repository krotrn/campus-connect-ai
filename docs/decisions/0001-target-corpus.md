# ADR 0001: Selection of Target Corpus

## Status
Accepted

## Date
2026-09-02

## Context
The AI Engineering Intelligence Assistant (AEIA) requires a representative, production-like software codebase to serve as the evaluation corpus. The codebase must support all seven core use cases defined in the PRD (architecture navigation, code location, change analysis, debugging assistance, dependency reasoning, onboarding, config/schema lookup).

A toy or artificial repository would not adequately evaluate code-aware parsing, multi-tier dependency mapping, or real-world documentation retrieval.

## Decision
We select [`coding-pundit-nitap/campus-connect`](https://github.com/coding-pundit-nitap/campus-connect) as the primary corpus for V1–V3.

Key characteristics:
- **Language / Framework**: TypeScript, Next.js (App Router), Node.js, Prisma ORM.
- **Scale**: 808 files, ~94,000 lines of code across source, tests, and configuration.
- **Documentation**: Includes extensive `ARCHITECTURE.md` (32 KB), `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and dedicated `docs/`.
- **Infrastructure & Config**: Multi-environment Docker compose configurations (`compose.dev.yml`, `compose.prod.yml`), Nginx config, and Prometheus/monitoring setups.
- **Data Layer**: Prisma schema (`prisma/schema.prisma`) and SQL migrations.
- **Git History**: Active commit and pull request history enabling git-based retrieval and change analysis (V5/V6).

## Consequences
- **Positive**: High architectural diversity (frontend, API routes, background workers, database, devops), providing rich ground-truth questions for the evaluation dataset.
- **Negative**: Language coverage in V1 is heavily focused on TypeScript/TSX and Markdown. Chunker must handle TS/TSX syntax rather than Python-only AST.

