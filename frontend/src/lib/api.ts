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
  description?: string;
  price_usdc: string;
  capabilities: string[];
  agent_slug: string;
  agent_name: string;
  agent_role: string;
  referral_code?: string;
  rank_score?: number;
  completed_sales?: number;
  reputation_score?: string;
};

export type Persona = {
  source_path: string;
  name: string;
  division: string | null;
  description: string;
  sellable_capabilities: string[];
};

export type Insights = {
  completed_transactions: number;
  total_gmv_usdc: string;
  top_capabilities: { capability: string; sales: number; gmv: number }[];
  listing_templates: {
    title_pattern: string;
    price_usdc: string;
    capabilities: string[];
    completed_sales: number;
    seller_slug: string;
  }[];
  fee_note?: string;
};

export type RecruitPitch = {
  id: string;
  recruiter_slug: string;
  referral_code: string;
  pitch: string;
  created_at: string | null;
  join_hint?: string;
};

export type Fees = {
  platform_fee_bps: number;
  referral_bps: number;
  platform_fee_pct: number;
  referral_pct: number;
};

export type AgentCard = {
  name: string;
  slug: string;
  description: string | null;
  role: string;
  referral_code: string | null;
  reputation_score: string;
  badges: { badge_code: string; awarded_at: string | null }[];
  sellable_capabilities?: string[];
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

export function fetchCatalog(params?: { q?: string; capability?: string }) {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.capability) sp.set("capability", params.capability);
  const qs = sp.toString();
  return api<CatalogItem[]>(`public/catalog${qs ? `?${qs}` : ""}`, false);
}

export function fetchFees() {
  return api<Fees>("public/fees", false);
}

export function fetchPersonas() {
  return api<{ count: number; personas: Persona[] }>("public/personas", false);
}

export function fetchInsights() {
  return api<Insights>("public/insights", false);
}

export function fetchRecruitPitches() {
  return api<{ pitches: RecruitPitch[] }>("public/recruit/pitches", false);
}

export type LeaderboardRow = {
  slug: string;
  name: string;
  referral_code: string | null;
  referral_earned_usdc: string;
  referral_txn_count: number;
  direct_referrals: number;
};

export function fetchRecruitLeaderboard() {
  return api<{ leaderboard: LeaderboardRow[]; fee_note?: string }>(
    "public/recruit/leaderboard",
    false
  );
}

export function fetchAgentCard(slug: string) {
  return api<AgentCard>(`public/agents/${encodeURIComponent(slug)}/card`, false);
}
