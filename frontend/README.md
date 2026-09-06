# NextJs - Production-Grade Next.js 16 Starter
# AEIA Web UI (Next.js + Vercel)

A robust, enterprise-ready template built with **Next.js 16**, **React 19**, **TypeScript**, **Tailwind CSS v4**, **shadcn/ui**, **Vitest**, and **Playwright**.
Modern, interactive Web UI console for the **AEIA (AI Engineering Intelligence Assistant)** system, built with **Next.js 16**, **React 19**, **TypeScript**, and **Tailwind CSS**.

---

## 🚀 Tech Stack & Features
## ⚡ Features

- **Framework**: [Next.js 16](https://nextjs.org/) (Turbopack, App Router under `src/app`)
- **Language**: [TypeScript](https://www.typescriptlang.org/) (Strict mode, path aliases `@/*`)
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/) (Base UI primitives + Lucide icons)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/) + `clsx` + `tailwind-merge`
- **Validation**: [Zod](https://zod.dev/) for type-safe environment schemas and API contracts
- **Unit & Component Testing**: [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/) + Happy-DOM
- **E2E Testing**: [Playwright](https://playwright.dev/) with automated web server lifecycle
- **Linting & Formatting**: [ESLint](https://eslint.org/) (Next.js config) + [Prettier](https://prettier.io/) + `prettier-plugin-tailwindcss`
- **Git Hooks**: [Husky](https://typicode.github.io/husky/) + [lint-staged](https://github.com/lint-staged/lint-staged)
- **CI / CD**: GitHub Actions workflow for linting, typechecking, tests, and production build
- **Hybrid RAG & LangGraph Agent Modes**: Switch seamlessly between fast direct 70/30 Dense+BM25 RRF search and multi-step LangGraph agent orchestration (git history, diff audits, dependency scans).
- **Real-Time Streaming**: Token-by-token streaming via Server-Sent Events (SSE) with instant source citation display.
- **Code Inspector Modal**: Interactive code preview modal with line numbers, file paths, relevance scoring, and 1-click clipboard copy.
- **Backend Health Polling**: Live status badge tracking Qdrant index health and total indexed vector chunks.
- **In-App Backend Configuration**: Flexible settings modal to configure or override the FastAPI backend URL and `X-API-Key` without redeploying.
- **Dark Mode First**: Clean, responsive terminal aesthetic styled with Tailwind CSS and shadcn/ui primitives.

---

## 📁 Directory Architecture
## 🚀 Quickstart (Local Development)

```
insta_hire_zetwork/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline
├── e2e/                         # Playwright End-to-End tests
│   ├── health.spec.ts           # Health API integration test
│   └── home.spec.ts             # Page rendering and user interaction tests
├── public/                      # Static assets
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── api/                 # API route handlers
│   │   │   └── health/route.ts  # Health check endpoint
│   │   ├── error.tsx            # App-level error boundary
│   │   ├── global-error.tsx     # Root error boundary
│   │   ├── layout.tsx           # Global Root layout
│   │   ├── loading.tsx          # Loading state indicator
│   │   ├── not-found.tsx        # Custom 404 page
│   │   └── page.tsx             # Interactive landing page demo
│   ├── components/              # UI Components
│   │   ├── common/              # Shared layout widgets (Header, Footer)
│   │   ├── feedback/            # Feedback indicators (LoadingSpinner, EmptyState)
│   │   └── ui/                  # shadcn/ui design tokens & primitives
│   ├── config/                  # App configuration & validated schemas
│   │   ├── env.ts               # Type-safe Zod environment validation
│   │   └── site.ts              # Site metadata and navigation constants
│   ├── hooks/                   # Custom reusable typed hooks
│   │   ├── use-debounce.ts      # Debounce state hook
│   │   ├── use-local-storage.ts # LocalStorage sync hook
│   │   └── use-media-query.ts   # useSyncExternalStore responsive hook
│   ├── lib/                     # Utilities & library helpers
│   │   ├── fetcher.ts           # Resilient HTTP fetcher with custom FetchError
│   │   └── utils.ts             # `cn` helper (clsx + tailwind-merge)
│   ├── styles/
│   │   └── globals.css          # Tailwind CSS tokens and themes
│   └── types/                   # Shared TypeScript interfaces & API models
│       └── index.ts
├── tests/                       # Vitest setup & helpers
│   ├── setup.ts                 # Jest-DOM matchers and window mocks
│   └── test-utils.tsx           # Custom React Testing Library render wrapper
├── .env.example                 # Documented environment template
├── .lintstagedrc.json           # Pre-commit staged linters
├── .prettierrc                  # Prettier config
├── components.json              # shadcn/ui configuration
├── next.config.ts               # Typed Next.js configuration
├── package.json                 # Dependency manifests & NPM scripts
├── playwright.config.ts         # Playwright E2E configuration
├── tsconfig.json                # Strict TypeScript configuration
└── vitest.config.mts            # Vitest runner configuration
```

---

## 🛠️ Getting Started

### 1. Prerequisites
- **Node.js**: `v20+` (v22 recommended)
- **Package Manager**: `pnpm` (v10 recommended)

### 2. Installation
### 1. Install Dependencies
```bash
# Clone the repository
git clone <repository-url>
cd insta_hire_zetwork

# Install dependencies
pnpm install
```

### 3. Environment Setup
### 2. Configure Environment (Optional)
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

### 4. Run Development Server
Configure your local or remote backend:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key-change-me
```

### 3. Run Development Server
```bash
pnpm run dev
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) to view the application.
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Available Scripts & Testing
## 🌐 Deploying to Vercel

| Command | Description |
| :--- | :--- |
| `pnpm run dev` | Start development server with Turbopack |
| `pnpm run build` | Create optimized production build |
| `pnpm run start` | Start production server |
| `pnpm run typecheck` | Run TypeScript compiler validation (`tsc --noEmit`) |
| `pnpm run lint` | Run ESLint checks |
| `pnpm run lint:fix` | Automatically fix ESLint warnings |
| `pnpm run format` | Format code using Prettier with Tailwind class ordering |
| `pnpm run test` | Run Unit & Component tests with Vitest |
| `pnpm run test:watch` | Run Vitest in interactive watch mode |
| `pnpm run test:coverage` | Generate code coverage report |
| `pnpm run test:e2e` | Run Playwright End-to-End test suite |
| `pnpm run test:e2e:ui` | Open interactive Playwright Test UI |
Deploying this UI to Vercel takes less than 2 minutes:

### Step 1: Import Repository to Vercel
1. Go to your [Vercel Dashboard](https://vercel.com/new).
2. Select and import your GitHub repository (`krotrn/campus-connect-ai` or `aeia`).

### Step 2: Configure Project Settings
In the Vercel project configuration screen:
- **Framework Preset**: `Next.js`
- **Root Directory**: Click **Edit** and select `frontend`

### Step 3: Set Environment Variables
Add the following Environment Variables in Vercel:
| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | URL of your deployed AEIA FastAPI backend | `https://aeia-backend.up.railway.app` |
| `NEXT_PUBLIC_API_KEY` | API Key configured on your backend (`API_KEY`) | `your-secret-api-key` |

> **Note**: Even after deployment, users can click the **Settings** button in the top right to point the UI to a different backend URL or test connections dynamically.

### Step 4: Deploy
Click **Deploy**. Vercel will build and deploy your Next.js frontend globally on their Edge Network!

---

## 🔒 Quality & CI Pipeline
## 🧪 Available Scripts

Every pull request and push to main runs our GitHub Actions workflow:
1. **ESLint**: Static analysis & lint rules
2. **TypeScript**: Strict typecheck
3. **Vitest**: Unit & Component tests
4. **Next.js Build**: Turbopack production compilation
| Command | Action |
| :--- | :--- |
| `pnpm dev` | Start development server on port 3000 |
| `pnpm build` | Create optimized production build |
| `pnpm start` | Start production server |
| `pnpm lint` | Run ESLint checks |
| `pnpm typecheck` | Run TypeScript compiler checks |
| `pnpm test` | Run Vitest unit/integration tests |
