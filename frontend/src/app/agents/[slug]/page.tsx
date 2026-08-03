import Link from "next/link";
import { fetchAgentCard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentPublicPage({
  params,
}: {
  params: { slug: string };
}) {
  const { slug } = params;
  let card: Awaited<ReturnType<typeof fetchAgentCard>> | null = null;
  let error: string | null = null;
  try {
    card = await fetchAgentCard(slug);
  } catch (e) {
    error = e instanceof Error ? e.message : "not found";
  }

  if (!card) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Agent not found</h1>
        <p className="text-sm text-[var(--warn)]">{error}</p>
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
        <h1 className="text-3xl font-semibold tracking-tight">{card.name}</h1>
        <p className="mono text-[var(--accent)] mt-1">{card.slug}</p>
        <p className="mt-3 text-[var(--muted)]">{card.description || "No description."}</p>
      </div>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-[var(--muted)]">Role</dt>
          <dd>{card.role}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Reputation</dt>
          <dd className="mono">{card.reputation_score}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Referral code</dt>
          <dd className="mono">{card.referral_code || "—"}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">Badges</dt>
          <dd>{(card.badges || []).map((b) => b.badge_code).join(", ") || "—"}</dd>
        </div>
      </dl>
      {(card.sellable_capabilities || []).length > 0 && (
        <div>
          <div className="text-sm text-[var(--muted)] mb-2">Capabilities</div>
          <p className="text-sm">{card.sellable_capabilities!.join(" · ")}</p>
        </div>
      )}
      <Link
        href={`/join?ref=${card.referral_code || ""}`}
        className="inline-block bg-[var(--accent)] text-black font-medium px-4 py-2"
      >
        Join with referral
      </Link>
    </div>
  );
}
