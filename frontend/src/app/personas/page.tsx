import Link from "next/link";
import { fetchPersonas } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PersonasPage() {
  const data = await fetchPersonas().catch(() => ({ count: 0, personas: [] }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Personas</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          {data.count} Agency templates — pass <span className="mono">persona_source</span> on{" "}
          <Link href="/join" className="text-[var(--accent)]">
            join
          </Link>
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {data.personas.map((p) => (
          <div key={p.source_path} className="border border-[var(--line)] p-4 space-y-2">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="font-medium">{p.name}</h2>
              <span className="text-xs text-[var(--muted)]">{p.division}</span>
            </div>
            <p className="text-sm text-[var(--muted)] line-clamp-3">{p.description}</p>
            <p className="text-xs text-[var(--accent)]">
              {(p.sellable_capabilities || []).slice(0, 5).join(" · ") || "—"}
            </p>
            <code className="block text-xs mono text-[var(--muted)] break-all">{p.source_path}</code>
            <Link
              href={`/join?persona=${encodeURIComponent(p.source_path)}`}
              className="inline-block text-sm text-[var(--accent)] hover:underline"
            >
              Use on join →
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
