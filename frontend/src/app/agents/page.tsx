import { fetchAgents } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const agents = await fetchAgents().catch(() => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Agents</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Registry + Turnkey wallet addresses (Base Sepolia)
        </p>
      </div>
      <div className="overflow-x-auto border border-[var(--line)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--bg-elev)] text-left text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 font-medium">Slug</th>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Role</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Wallet</th>
              <th className="px-3 py-2 font-medium">Reputation</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id} className="border-t border-[var(--line)]">
                <td className="px-3 py-2 mono text-[var(--accent)]">{a.slug}</td>
                <td className="px-3 py-2">{a.name}</td>
                <td className="px-3 py-2">{a.role}</td>
                <td className="px-3 py-2">{a.status}</td>
                <td className="px-3 py-2 mono text-xs">
                  {a.wallet_address
                    ? `${a.wallet_address.slice(0, 6)}…${a.wallet_address.slice(-4)}`
                    : "—"}
                </td>
                <td className="px-3 py-2 mono">{a.reputation_score}</td>
              </tr>
            ))}
            {agents.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-[var(--muted)]">
                  No agents (is the backend running?)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
