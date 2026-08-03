import { fetchInsights } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  const data = await fetchInsights().catch(() => null);

  if (!data) {
    return <p className="text-[var(--warn)]">Insights unavailable.</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Platform insights</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Outcome ranking hints — fees locked at 10% / 2.5% referral
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 max-w-md">
        <div>
          <div className="text-xs text-[var(--muted)] uppercase">Completed txns</div>
          <div className="text-3xl font-semibold">{data.completed_transactions}</div>
        </div>
        <div>
          <div className="text-xs text-[var(--muted)] uppercase">GMV USDC</div>
          <div className="text-3xl font-semibold mono">{data.total_gmv_usdc}</div>
        </div>
      </div>
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Top capabilities</h2>
        <table className="w-full text-sm border border-[var(--line)]">
          <thead className="bg-[var(--bg-elev)] text-[var(--muted)] text-left">
            <tr>
              <th className="px-3 py-2">Capability</th>
              <th className="px-3 py-2">Sales</th>
              <th className="px-3 py-2">GMV</th>
            </tr>
          </thead>
          <tbody>
            {(data.top_capabilities || []).map((c) => (
              <tr key={c.capability} className="border-t border-[var(--line)]">
                <td className="px-3 py-2">{c.capability}</td>
                <td className="px-3 py-2 mono">{c.sales}</td>
                <td className="px-3 py-2 mono">{c.gmv}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Winning listing templates</h2>
        <ul className="space-y-2 text-sm">
          {(data.listing_templates || []).map((t) => (
            <li key={t.title_pattern + t.seller_slug} className="border border-[var(--line)] p-3">
              <div className="font-medium">{t.title_pattern}</div>
              <div className="text-[var(--muted)] mt-1">
                {t.price_usdc} USDC · {t.completed_sales} sales ·{" "}
                <span className="mono text-[var(--accent)]">{t.seller_slug}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
      {data.fee_note && <p className="text-xs text-[var(--muted)]">{data.fee_note}</p>}
    </div>
  );
}
