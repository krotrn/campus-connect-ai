export interface NavItem {
  title: string;
  href: string;
  disabled?: boolean;
  external?: boolean;
}

export const siteConfig = {
  name: "NextJs",
  description:
    "Production-grade Next.js starter with TypeScript, Tailwind CSS, Vitest, React Testing Library, and Playwright.",
  url: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ogImage: "https://og-image.vercel.app/NextJs.png",
  mainNav: [
    {
      title: "Home",
      href: "/",
    },
    {
      title: "Features",
      href: "/#features",
    },
    {
      title: "Docs",
      href: "/#docs",
    },
  ] as NavItem[],
  links: {
    github: "https://github.com",
    twitter: "https://twitter.com",
  },
};
