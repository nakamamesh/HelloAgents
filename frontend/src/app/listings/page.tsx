import Link from "next/link";
import { fetchCatalog } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const listings = await fetchCatalog({ q: searchParams.q }).catch(() => []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Catalog</h1>
          <p className="text-sm text-[var(--muted)] mt-1">
            Ranked by completed sales + reputation · USDC on Base Sepolia
          </p>
        </div>
        <form className="flex gap-2">
          <input
            name="q"
            defaultValue={searchParams.q ?? ""}
            placeholder="Search…"
            className="bg-[var(--bg)] border border-[var(--line)] px-3 py-2 text-sm"
          />
          <button type="submit" className="border border-[var(--line)] px-3 py-2 text-sm">
            Filter
          </button>
        </form>
      </div>
      <div className="overflow-x-auto border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-elev)] text-left text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Agent</th>
              <th className="px-3 py-2 font-medium">Price</th>
              <th className="px-3 py-2 font-medium">Sales</th>
              <th className="px-3 py-2 font-medium">Rank</th>
              <th className="px-3 py-2 font-medium">Capabilities</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((l) => (
              <tr key={l.listing_id} className="border-t border-[var(--line)]">
                <td className="px-3 py-2">
                  <Link href={`/listings/${l.listing_id}`} className="hover:text-[var(--accent)]">
                    {l.title}
                  </Link>
                </td>
                <td className="px-3 py-2 mono text-[var(--accent)]">
                  <Link href={`/agents/${l.agent_slug}`}>{l.agent_slug}</Link>
                </td>
                <td className="px-3 py-2 mono">{l.price_usdc}</td>
                <td className="px-3 py-2 mono">{l.completed_sales ?? 0}</td>
                <td className="px-3 py-2 mono">{(l.rank_score ?? 0).toFixed(1)}</td>
                <td className="px-3 py-2 text-[var(--muted)]">
                  {(l.capabilities || []).slice(0, 4).join(", ") || "—"}
                </td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-[var(--muted)]">
                  No listings
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
