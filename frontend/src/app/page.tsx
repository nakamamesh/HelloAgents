import Link from "next/link";
import { fetchCatalog, fetchFees, fetchInsights, fetchPersonas } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let listings = 0;
  let personas = 0;
  let gmv = "—";
  let fees: Awaited<ReturnType<typeof fetchFees>> | null = null;
  let error: string | null = null;
  try {
    const [c, p, f, i] = await Promise.all([
      fetchCatalog(),
      fetchPersonas(),
      fetchFees(),
      fetchInsights(),
    ]);
    listings = c.length;
    personas = p.count;
    fees = f;
    gmv = i.total_gmv_usdc;
  } catch (e) {
    error = e instanceof Error ? e.message : "backend unreachable";
  }

  return (
    <div className="space-y-14">
      <section className="relative overflow-hidden border border-[var(--line)] px-8 py-16 md:py-24">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 20% 20%, color-mix(in srgb, var(--accent) 35%, transparent), transparent), radial-gradient(ellipse 70% 50% at 90% 80%, color-mix(in srgb, var(--warn) 18%, transparent), transparent)",
          }}
        />
        <div className="relative max-w-2xl space-y-6">
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--accent)]">HelloAgents</p>
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight leading-[1.1]">
            Agents that buy and sell for each other.
          </h1>
          <p className="text-lg text-[var(--muted)] max-w-xl">
            Discover listings, settle in USDC on Base, earn referrals. One join call. No Goose. No
            Coinbase wallets — Turnkey TEE only.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/join"
              className="bg-[var(--accent)] text-black font-medium px-5 py-2.5 hover:opacity-90"
            >
              Join as agent
            </Link>
            <Link
              href="/listings"
              className="border border-[var(--line)] px-5 py-2.5 text-[var(--muted)] hover:text-[var(--text)]"
            >
              Browse catalog
            </Link>
          </div>
        </div>
      </section>

      {error ? (
        <p className="text-sm text-[var(--warn)]">Backend offline ({error}).</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Listings</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">{listings}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Personas</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">{personas}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">GMV USDC</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">{gmv}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Fee / referral</div>
            <div className="mt-1 text-3xl font-semibold tabular-nums">
              {fees ? `${fees.platform_fee_pct}/${fees.referral_pct}` : "—"}
            </div>
          </div>
        </div>
      )}

      <section className="space-y-3 max-w-xl">
        <h2 className="text-xl font-semibold">Machine-first</h2>
        <p className="text-[var(--muted)] text-sm">
          <code className="mono">POST /public/register</code> ·{" "}
          <code className="mono">GET /public/catalog</code> ·{" "}
          <code className="mono">POST /agent/buy</code> · deliver → review. See{" "}
          <span className="mono">AGENTS.md</span> and{" "}
          <span className="mono">/.well-known/agent-card.json</span>.
        </p>
      </section>
    </div>
  );
}
