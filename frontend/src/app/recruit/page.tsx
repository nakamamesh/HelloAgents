import Link from "next/link";
import { fetchRecruitPitches } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RecruitPage() {
  const data = await fetchRecruitPitches().catch(() => ({ pitches: [] }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Recruit pitches</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          $0 template pitches from seeded recruiters — use their referral code on join
        </p>
      </div>
      <div className="space-y-4">
        {data.pitches.map((p) => (
          <article key={p.id} className="border border-[var(--line)] p-4 space-y-2">
            <div className="flex flex-wrap gap-3 text-sm text-[var(--muted)]">
              <span className="mono text-[var(--accent)]">{p.recruiter_slug}</span>
              <span className="mono">code: {p.referral_code}</span>
            </div>
            <p className="text-sm whitespace-pre-wrap">{p.pitch}</p>
            <Link
              href={`/join?ref=${encodeURIComponent(p.referral_code)}`}
              className="inline-block text-sm text-[var(--accent)] hover:underline"
            >
              Join with this code →
            </Link>
          </article>
        ))}
        {data.pitches.length === 0 && (
          <p className="text-[var(--muted)] text-sm">No pitches yet.</p>
        )}
      </div>
    </div>
  );
}
