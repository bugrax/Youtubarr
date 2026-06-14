export interface Film {
  id: number;
  tmdb_id: number;
  title: string;
  original_title: string;
  year: number | null;
  runtime: number;
  status: string;
  youtube_id: string | null;
  youtube_title: string | null;
  youtube_channel: string | null;
  match_score: number | null;
  source: string;
}

export interface Job {
  id: number;
  film_id: number;
  youtube_id: string;
  state: string;
  progress: number;
  speed: string | null;
  eta: string | null;
  message: string | null;
}

export interface Health {
  version: string;
  radarr: { configured: boolean; ok?: boolean; version?: string; error?: string };
}

async function j<T>(path: string, method = "GET"): Promise<T> {
  const r = await fetch(path, { method });
  return r.json();
}

export const api = {
  health: () => j<Health>("/api/health"),
  stats: () => j<Record<string, number>>("/api/stats"),
  films: (status?: string) => j<Film[]>(`/api/films${status ? `?status=${status}` : ""}`),
  jobs: () => j<Job[]>("/api/jobs"),
  sync: () => j("/api/sync", "POST"),
  searchAll: () => j("/api/search", "POST"),
  tmdbSync: () => j("/api/tmdb/sync", "POST"),
  pollChannels: () => j("/api/channels/poll", "POST"),
  searchOne: (id: number) => j(`/api/films/${id}/search`),
  grab: (id: number) => j(`/api/films/${id}/grab`, "POST"),
  blocklist: (id: number) => j(`/api/films/${id}/blocklist`, "POST"),
};
