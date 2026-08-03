export type Agent = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  role: string;
  status: string;
  reputation_score: string;
  referral_budget: string;
  wallet_address?: string | null;
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

export type CatalogItem = {
  listing_id: string;
  title: string;
  price_usdc: string;
  capabilities: string[];
  agent_slug: string;
  agent_name: string;
  agent_role: string;
  referral_code?: string;
};

export type Fees = {
  platform_fee_bps: number;
  referral_bps: number;
  platform_fee_pct: number;
  referral_pct: number;
};

function backendBase() {
  return process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
}

async function api<T>(path: string, admin = true): Promise<T> {
  const headers: Record<string, string> = {};
  if (admin) headers["X-Admin-Key"] = process.env.ADMIN_API_KEY ?? "";
  const res = await fetch(`${backendBase()}/${path}`, {
    cache: "no-store",
    headers,
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

export function fetchCatalog() {
  return api<CatalogItem[]>("public/catalog", false);
}

export function fetchFees() {
  return api<Fees>("public/fees", false);
}
