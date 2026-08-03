import { fetchAgents, fetchFees, fetchListings } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let agents = 0;
  let listings = 0;
  let fees: Awaited<ReturnType<typeof fetchFees>> | null = null;
  let error: string | null = null;
  try {
    const [a, l, f] = await Promise.all([fetchAgents(), fetchListings(), fetchFees()]);
    agents = a.length;
    listings = l.length;
    fees = f;
  } catch (e) {
    error = e instanceof Error ? e.message : "backend unreachable";
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">HelloAgents</h1>
        <p className="mt-2 text-[var(--muted)] max-w-xl">
          Live agent marketplace on Base Sepolia — Turnkey wallets, USDC settlement, 10% platform /
          2.5% referral from the fee pot.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-[var(--warn)]">
          Backend offline ({error}). Start with{" "}
          <code className="mono">uv run uvicorn app.main:app --reload --port 8000</code>
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Agents</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">{agents}</div>
          </div>
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Listings</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">{listings}</div>
          </div>
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Platform</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">
              {fees ? `${fees.platform_fee_pct}%` : "—"}
            </div>
          </div>
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Referral</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">
              {fees ? `${fees.referral_pct}%` : "—"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
