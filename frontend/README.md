# AEIA Web UI Console (Next.js + Vercel)

A modern, responsive web console for the **AEIA (AI Engineering Intelligence Assistant)** system, built with **Next.js 16**, **React 19**, **TypeScript**, **Tailwind CSS v4**, and **shadcn/ui**.

---

## ⚡ Features

- **Hybrid RAG & LangGraph Agent Modes**: Switch seamlessly between fast direct 70/30 Dense+BM25 RRF search and multi-step LangGraph agent orchestration (git history, diff audits, dependency scans).
- **Real-Time SSE Streaming**: Token-by-token streaming via Server-Sent Events (SSE) with instant source citation display ([ADR 0030](../docs/decisions/0030-unified-sse-streaming-protocol-for-rag-and-agent.md)).
- **Code Inspector Modal**: Interactive slide-over drawer with line numbers, file paths, relevance scoring, and 1-click clipboard copy for verified citations.
- **Client-Side Gemini API Key Injection**: In-app settings dialog allowing users to supply their personal Gemini API key, stored only in browser `localStorage`, bypassing shared server quota limits ([ADR 0029](../docs/decisions/0029-client-side-api-key-injection-and-quota-resilience.md)).
- **Quota Alert & Auto-Retry**: Animated countdown timer and 1-click retry modal on HTTP 429 quota exhaustion.
- **Backend Health Polling**: Live status indicator tracking Qdrant index health and total indexed vector chunks via React Query.
- **Dark Mode First**: Clean terminal aesthetic styled with Tailwind CSS v4 and `shadcn/ui` primitives.
- **Comprehensive Test Suite**: Component and unit tests via Vitest; end-to-end browser tests via Playwright.

---

## 📁 Directory Architecture

```
frontend/
├── e2e/                         # Playwright End-to-End tests
│   ├── health.spec.ts           # Health API integration test
│   └── home.spec.ts             # Page rendering and user interaction tests
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── api/health/route.ts  # Health check endpoint
│   │   ├── error.tsx            # App-level error boundary
│   │   ├── global-error.tsx     # Root error boundary
│   │   ├── layout.tsx           # Global Root layout
│   │   ├── loading.tsx          # Loading state indicator
│   │   ├── not-found.tsx        # Custom 404 page
│   │   └── page.tsx             # Interactive landing page console
│   ├── components/
│   │   ├── aeia/                # AEIA domain components
│   │   │   ├── answer-card.tsx    # Streaming markdown renderer
│   │   │   ├── citation-list.tsx  # Citation chips grid
│   │   │   ├── code-modal.tsx     # Slide-over chunk code viewer
│   │   │   ├── mode-selector.tsx  # Direct RAG vs Agent toggle
│   │   │   ├── query-input.tsx    # Multi-line search textarea
│   │   │   ├── quota-alert.tsx    # HTTP 429 recovery countdown
│   │   │   ├── settings-dialog.tsx# Backend & Gemini API key modal
│   │   │   └── telemetry-bar.tsx  # Route, latency, and token audits
│   │   ├── common/              # Layout widgets (Header, Footer)
│   │   ├── feedback/            # Feedback indicators (LoadingSpinner, EmptyState)
│   │   └── ui/                  # shadcn/ui design tokens & primitives
│   ├── config/                  # App configuration & site metadata
│   ├── hooks/                   # Custom hooks (useDebounce, useLocalStorage, useHealth)
│   ├── lib/                     # Utilities (fetcher, settings, cn)
│   ├── services/                # API clients (aeia.service.ts for SSE streaming)
│   └── types/                   # TypeScript schemas and models
├── tests/                       # Vitest setup & test utilities
├── package.json                 # Dependency manifests & NPM scripts
├── playwright.config.ts         # Playwright E2E configuration
├── tsconfig.json                # Strict TypeScript configuration
└── vitest.config.mts            # Vitest runner configuration
```

---

## 🚀 Quickstart (Local Development)

### 1. Prerequisites
- **Node.js**: `v20+` (v22 recommended)
- **Package Manager**: `pnpm` (v10 recommended)
- **AEIA Backend**: Running on `http://localhost:8000`

### 2. Install Dependencies
```bash
cd frontend
pnpm install
```

### 3. Configure Environment (Optional)
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```
Defaults configured in `.env.example`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key-change-me
```

### 4. Run Development Server
```bash
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🌐 Deploying to Vercel

Deploying the console to Vercel takes under 2 minutes:

1. Import your GitHub repository into your [Vercel Dashboard](https://vercel.com/new).
2. Configure project settings:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `frontend`
3. Configure Environment Variables:
   - `NEXT_PUBLIC_API_URL`: URL of your deployed AEIA FastAPI backend (e.g. `https://aeia.onrender.com` or Railway URL).
   - `NEXT_PUBLIC_API_KEY`: API Key configured on your backend (`API_KEY`).
4. Click **Deploy**. Vercel will build and distribute your frontend globally on their Edge Network.

> **Note**: Users can also configure or override the backend URL and Gemini API key dynamically via the **Settings** dialog in the UI header.

---

## 🧪 Available Scripts & Testing

| Command | Description |
| :--- | :--- |
| `pnpm dev` | Start development server with Turbopack on port 3000 |
| `pnpm build` | Create optimized production build |
| `pnpm start` | Start production server |
| `pnpm lint` | Run ESLint static analysis checks |
| `pnpm typecheck` | Run strict TypeScript compiler validation (`tsc --noEmit`) |
| `pnpm test` | Run Unit & Component tests with Vitest |
| `pnpm test:watch` | Run Vitest in interactive watch mode |
| `pnpm test:coverage` | Generate Vitest code coverage report |
| `pnpm test:e2e` | Run Playwright End-to-End browser tests |
