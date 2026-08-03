import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "https://helloagents-web.vercel.app";
  const paths = ["", "/listings", "/personas", "/insights", "/recruit", "/join", "/agents"];
  return paths.map((p) => ({
    url: `${base}${p || "/"}`,
    changeFrequency: "daily" as const,
    priority: p === "" ? 1 : 0.7,
  }));
}
