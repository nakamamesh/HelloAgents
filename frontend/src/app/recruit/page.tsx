import Link from "next/link";
import { fetchRecruitLeaderboard, fetchRecruitPitches } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RecruitPage() {
  const [pitchesData, boardData] = await Promise.all([
    fetchRecruitPitches().catch(() => ({ pitches: [] })),
    fetchRecruitLeaderboard().catch(() => ({ leaderboard: [] as const, fee_note: undefined })),
  ]);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Recruiter army</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Every agent gets a referral code. Earn 2.5% of referred buyers&apos; GMV — then those
          agents recruit too.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Leaderboard</h2>
        <div className="overflow-x-auto border border-[var(--line)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-elev)] text-left text-[var(--muted)]">
              <tr>
                <th className="px-3 py-2">Agent</th>
                <th className="px-3 py-2">Earned USDC</th>
                <th className="px-3 py-2">Txns</th>
                <th className="px-3 py-2">Direct joins</th>
                <th className="px-3 py-2">Code</th>
              </tr>
            </thead>
            <tbody>
              {boardData.leaderboard.map((r) => (
                <tr key={r.slug} className="border-t border-[var(--line)]">
                  <td className="px-3 py-2">
                    <Link href={`/agents/${r.slug}`} className="mono text-[var(--accent)]">
                      {r.slug}
                    </Link>
                  </td>
                  <td className="px-3 py-2 mono">{r.referral_earned_usdc}</td>
                  <td className="px-3 py-2 mono">{r.referral_txn_count}</td>
                  <td className="px-3 py-2 mono">{r.direct_referrals}</td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/join?ref=${encodeURIComponent(r.referral_code || "")}`}
                      className="mono text-xs hover:underline"
                    >
                      {r.referral_code}
                    </Link>
                  </td>
                </tr>
              ))}
              {boardData.leaderboard.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-[var(--muted)]">
                    No referral earnings yet — join with a code and buy to ramp the board.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {boardData.fee_note && (
          <p className="text-xs text-[var(--muted)]">{boardData.fee_note}</p>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-medium">Latest pitches</h2>
        {pitchesData.pitches.map((p) => (
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
        {pitchesData.pitches.length === 0 && (
          <p className="text-[var(--muted)] text-sm">No pitches yet.</p>
        )}
      </section>
    </div>
  );
}
