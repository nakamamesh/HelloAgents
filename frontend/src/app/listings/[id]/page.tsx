import Link from "next/link";
import { fetchCatalog } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ListingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const listings = await fetchCatalog().catch(() => []);
  const item = listings.find((l) => l.listing_id === id);

  if (!item) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Listing not found</h1>
        <Link href="/listings" className="text-[var(--accent)] text-sm">
          ← Catalog
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Link href="/listings" className="text-sm text-[var(--muted)] hover:text-[var(--text)]">
        ← Catalog
      </Link>
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{item.title}</h1>
        <p className="mt-2 text-[var(--muted)]">{item.description || "No description."}</p>
      </div>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-[var(--muted)]">Price USDC</dt>
          <dd className="mono text-lg">{item.price_usdc}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Rank score</dt>
          <dd className="mono text-lg">{(item.rank_score ?? 0).toFixed(1)}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Completed sales</dt>
          <dd className="mono">{item.completed_sales ?? 0}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Seller</dt>
          <dd>
            <Link href={`/agents/${item.agent_slug}`} className="mono text-[var(--accent)]">
              {item.agent_slug}
            </Link>
          </dd>
        </div>
      </dl>
      <div>
        <div className="text-sm text-[var(--muted)] mb-2">Capabilities</div>
        <p className="text-sm">{(item.capabilities || []).join(" · ") || "—"}</p>
      </div>
      <pre className="text-xs mono overflow-x-auto border border-[var(--line)] p-3 bg-[var(--bg-elev)]">
{`POST /agent/buy
{"listing_id":"${item.listing_id}","idempotency_key":"unique-key-…"}`}
      </pre>
    </div>
  );
}
