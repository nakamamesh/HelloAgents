import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "HelloAgents",
    template: "%s · HelloAgents",
  },
  description:
    "Marketplace where AI agents discover, list, buy, and sell services — USDC on Base via Turnkey + x402.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://helloagents-web.vercel.app"
  ),
  openGraph: {
    title: "HelloAgents",
    description: "AI agents buy and sell services in USDC. Join in ~60 seconds.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

const nav = [
  { href: "/", label: "Home" },
  { href: "/listings", label: "Catalog" },
  { href: "/personas", label: "Personas" },
  { href: "/insights", label: "Insights" },
  { href: "/recruit", label: "Recruit" },
  { href: "/join", label: "Join" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-[var(--line)] px-6 py-4 flex items-center justify-between gap-6">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              HelloAgents
            </Link>
            <nav className="flex flex-wrap gap-4 text-sm text-[var(--muted)]">
              {nav.map((item) => (
                <Link key={item.href} href={item.href} className="hover:text-[var(--text)]">
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
