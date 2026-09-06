export interface NavItem {
  title: string;
  href: string;
  disabled?: boolean;
  external?: boolean;
}

export const siteConfig = {
  name: "AEIA",
  description:
    "AI Engineering Intelligence Assistant — Agentic RAG and code intelligence for Campus Connect (~94k LOC).",
  url: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ogImage: "https://og-image.vercel.app/AEIA.png",
  mainNav: [
    {
      title: "Console",
      href: "/",
    },
    {
      title: "Documentation",
      href: "/docs",
    },
    {
      title: "Docs",
      href: "/#docs",
    },
  ] as NavItem[],
  links: {
    twitter: "https://twitter.com",
    github: "https://github.com/krotrn/campus-connect-ai",
    docs: "/docs",
  },
};
