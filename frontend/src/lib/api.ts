export type Agent = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  role: string;
  status: string;
  reputation_score: string;
  referral_budget: string;
  created_at: string;
};

export type Listing = {
  id: string;
  agent_id: string;
  title: string;
  description: string | null;
  price_usdc: string;
  status: string;
  capabilities: string[];
  created_at: string;
};

function backendBase() {
  return process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
}

async function api<T>(path: string): Promise<T> {
  const res = await fetch(`${backendBase()}/${path}`, {
    cache: "no-store",
    headers: { "X-Admin-Key": process.env.ADMIN_API_KEY ?? "" },
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchAgents() {
  return api<Agent[]>("agents");
}

export function fetchListings() {
  return api<Listing[]>("listings");
}
