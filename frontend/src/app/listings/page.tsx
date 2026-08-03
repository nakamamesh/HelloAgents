import { fetchCatalog } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ListingsPage() {
  const listings = await fetchCatalog().catch(() => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Catalog</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Public marketplace — prices in USDC on Base Sepolia
        </p>
      </div>
      <div className="overflow-x-auto border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-elev)] text-left text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Agent</th>
              <th className="px-3 py-2 font-medium">Price USDC</th>
              <th className="px-3 py-2 font-medium">Capabilities</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((l) => (
              <tr key={l.listing_id} className="border-t border-[var(--line)]">
                <td className="px-3 py-2">{l.title}</td>
                <td className="px-3 py-2 mono text-[var(--accent)]">{l.agent_slug}</td>
                <td className="px-3 py-2 mono">{l.price_usdc}</td>
                <td className="px-3 py-2 text-[var(--muted)]">
                  {(l.capabilities || []).slice(0, 3).join(", ") || "—"}
                </td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-[var(--muted)]">
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
