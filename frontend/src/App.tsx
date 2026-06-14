import { useCallback, useEffect, useState } from "react";
import { api, type Film, type Health, type Job } from "./api";

const STATUSES = ["", "wanted", "matched", "downloading", "imported", "failed"];

function Badge({ s }: { s: string }) {
  return <span className={`badge ${s}`}>{s}</span>;
}

function Confidence({ score }: { score: number | null }) {
  if (score == null) return <span className="muted">—</span>;
  const cls = score >= 0.75 ? "high" : score >= 0.6 ? "medium" : "low";
  return <span className={cls}>{score.toFixed(2)}</span>;
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [films, setFilms] = useState<Film[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [f, s, j] = await Promise.all([
      api.films(filter || undefined),
      api.stats(),
      api.jobs(),
    ]);
    setFilms(f);
    setStats(s);
    setJobs(j);
  }, [filter]);

  useEffect(() => {
    api.health().then(setHealth);
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);
  useEffect(() => {
    const t = setInterval(() => api.jobs().then(setJobs), 3000);
    return () => clearInterval(t);
  }, []);

  const run = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    try {
      await fn();
      await refresh();
    } finally {
      setBusy(null);
    }
  };

  const r = health?.radarr;
  return (
    <div className="wrap">
      <header>
        <h1>🎬 Youtubarr</h1>
        <span className="muted">
          {r?.configured
            ? r.ok
              ? `Radarr v${r.version} bağlı ✓`
              : `Radarr hata: ${r.error}`
            : "Radarr ayarlı değil"}
        </span>
      </header>

      <div className="bar">
        <button disabled={!!busy} onClick={() => run("sync", api.sync)}>
          {busy === "sync" ? "…" : "↻ Radarr senkron"}
        </button>
        <button disabled={!!busy} onClick={() => run("search", api.searchAll)}>
          {busy === "search" ? "aranıyor…" : "🔍 Wanted'ı ara"}
        </button>
        <button className="ghost" disabled={!!busy} onClick={() => run("tmdb", api.tmdbSync)}>
          {busy === "tmdb" ? "…" : "＋ TMDB listesi"}
        </button>
        <button className="ghost" disabled={!!busy} onClick={() => run("chan", api.pollChannels)}>
          {busy === "chan" ? "…" : "📡 Kanal feed"}
        </button>
        <span className="stats">
          {STATUSES.filter(Boolean).map((s) => (
            <span key={s} className="pill" onClick={() => setFilter(s)}>
              {s}: <b>{stats[s] ?? 0}</b>
            </span>
          ))}
          {filter && (
            <span className="pill clear" onClick={() => setFilter("")}>
              ✕ filtre
            </span>
          )}
        </span>
      </div>

      <table>
        <thead>
          <tr>
            <th>Film</th>
            <th>Yıl</th>
            <th>Süre</th>
            <th>Durum</th>
            <th>YouTube eşleşme</th>
            <th>Skor</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {films.map((f) => (
            <tr key={f.id}>
              <td>
                {f.original_title || f.title}
                {f.source === "tmdb" && <span className="src">tmdb</span>}
              </td>
              <td>{f.year}</td>
              <td>{f.runtime ? `${f.runtime}dk` : ""}</td>
              <td>
                <Badge s={f.status} />
              </td>
              <td>
                {f.youtube_id ? (
                  <a href={`https://youtu.be/${f.youtube_id}`} target="_blank" rel="noreferrer">
                    {(f.youtube_title || "").slice(0, 42)}
                    <div className="muted">{f.youtube_channel}</div>
                  </a>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>
                <Confidence score={f.match_score} />
              </td>
              <td className="actions">
                <button className="mini" onClick={() => api.searchOne(f.id).then(refresh)}>
                  🔍
                </button>
                {f.youtube_id && (
                  <>
                    <button className="mini" onClick={() => api.grab(f.id).then(refresh)}>
                      ⬇
                    </button>
                    <button className="mini ghost" onClick={() => api.blocklist(f.id).then(refresh)}>
                      ✕
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>İndirme kuyruğu</h2>
      <table>
        <thead>
          <tr>
            <th>Film</th>
            <th>Durum</th>
            <th>İlerleme</th>
            <th>Hız</th>
            <th>ETA</th>
            <th>Mesaj</th>
          </tr>
        </thead>
        <tbody>
          {jobs.slice(0, 25).map((jb) => (
            <tr key={jb.id}>
              <td>#{jb.film_id}</td>
              <td>
                <Badge s={jb.state} />
              </td>
              <td>
                <div className="minibar">
                  <div className="fill" style={{ width: `${jb.progress}%` }} />
                </div>
                {jb.progress}%
              </td>
              <td>{jb.speed}</td>
              <td>{jb.eta}</td>
              <td className="muted">{jb.message}</td>
            </tr>
          ))}
          {jobs.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                kuyruk boş
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
