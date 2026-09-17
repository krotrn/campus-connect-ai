import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import { siteConfig } from "@/config/site";
import { Providers } from "@/providers";
import "./globals.css";

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: siteConfig.name,
    template: `%s | ${siteConfig.name}`,
  },
  description: siteConfig.description,
  metadataBase: new URL(siteConfig.url),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${jetbrainsMono.variable} dark h-full antialiased`}
    >
      <body className="h-full w-full bg-[#0b0a08] font-mono text-stone-100 overflow-hidden antialiased selection:bg-moss-500/30 selection:text-moss-300">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
