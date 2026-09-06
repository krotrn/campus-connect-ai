# NextJs - Production-Grade Next.js 16 Starter

A robust, enterprise-ready template built with **Next.js 16**, **React 19**, **TypeScript**, **Tailwind CSS v4**, **shadcn/ui**, **Vitest**, and **Playwright**.

---

## 🚀 Tech Stack & Features

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

---

## 📁 Directory Architecture

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
```bash
# Clone the repository
git clone <repository-url>
cd insta_hire_zetwork

# Install dependencies
pnpm install
```

### 3. Environment Setup
```bash
cp .env.example .env.local
```

### 4. Run Development Server
```bash
pnpm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the application.

---

## 🧪 Available Scripts & Testing

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

---

## 🔒 Quality & CI Pipeline

Every pull request and push to main runs our GitHub Actions workflow:
1. **ESLint**: Static analysis & lint rules
2. **TypeScript**: Strict typecheck
3. **Vitest**: Unit & Component tests
4. **Next.js Build**: Turbopack production compilation
