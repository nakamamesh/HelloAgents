import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "HelloAgents Admin",
  description: "Control plane dashboard for the HelloAgents marketplace",
};

const nav = [
  { href: "/", label: "Overview" },
  { href: "/agents", label: "Agents" },
  { href: "/listings", label: "Catalog" },
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
            <nav className="flex gap-4 text-sm text-[var(--muted)]">
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
