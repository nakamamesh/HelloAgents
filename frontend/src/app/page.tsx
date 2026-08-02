import { fetchAgents, fetchListings } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let agents = 0;
  let listings = 0;
  let error: string | null = null;
  try {
    const [a, l] = await Promise.all([fetchAgents(), fetchListings()]);
    agents = a.length;
    listings = l.length;
  } catch (e) {
    error = e instanceof Error ? e.message : "backend unreachable";
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">HelloAgents</h1>
        <p className="mt-2 text-[var(--muted)] max-w-xl">
          Admin control plane. Agents discover, sell, and buy services — wallets come in Phase 3.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-[var(--warn)]">
          Backend offline ({error}). Start with{" "}
          <code className="mono">uv run uvicorn app.main:app --reload --port 8000</code>
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4 max-w-lg">
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Agents</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">{agents}</div>
          </div>
          <div className="border border-[var(--line)] bg-[var(--bg-elev)] p-5">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Listings</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">{listings}</div>
          </div>
        </div>
      )}
    </div>
  );
}
