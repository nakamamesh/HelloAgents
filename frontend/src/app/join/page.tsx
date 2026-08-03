import { Suspense } from "react";
import JoinForm from "./join-form";

export default function JoinPage() {
  return (
    <Suspense fallback={<p className="text-[var(--muted)]">Loading…</p>}>
      <JoinForm />
    </Suspense>
  );
}
