export interface NavItem {
  title: string;
  href: string;
  disabled?: boolean;
  external?: boolean;
}

export const siteConfig = {
  name: "NextJs",
  name: "AEIA",
  description:
    "Production-grade Next.js starter with TypeScript, Tailwind CSS, Vitest, React Testing Library, and Playwright.",
    "AI Engineering Intelligence Assistant — Agentic RAG and code intelligence for Campus Connect (~94k LOC).",
  url: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ogImage: "https://og-image.vercel.app/NextJs.png",
  ogImage: "https://og-image.vercel.app/AEIA.png",
  mainNav: [
    {
      title: "Home",
      title: "Console",
      href: "/",
    },
    {
      title: "Features",
      href: "/#features",
      title: "Documentation",
      href: "/docs",
    },
    {
      title: "Docs",
      href: "/#docs",
    },
  ] as NavItem[],
  links: {
    github: "https://github.com",
    twitter: "https://twitter.com",
    github: "https://github.com/krotrn/campus-connect-ai",
    docs: "/docs",
  },
};
