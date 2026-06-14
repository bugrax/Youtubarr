import { useCallback, useEffect, useState } from "react";
import { api, type Film, type Health, type Job } from "./api";

const STATUSES = ["wanted", "matched", "downloading", "imported", "failed"];
const ACTIVE = ["downloading", "importing", "queued"];

function Badge({ s }: { s: string }) {
  return <span className={`badge ${s}`}>{s}</span>;
}

function Confidence({ score }: { score: number | null }) {
  if (score == null) return <span className="muted">—</span>;
  const cls = score >= 0.75 ? "high" : score >= 0.6 ? "medium" : "low";
  return <span className={cls}>{score.toFixed(2)}</span>;
}

function JobCard({ job, onRetry }: { job: Job; onRetry: (id: number) => void }) {
  return (
    <div className="job">
      <div className="job-top">
        <span className="job-title">
          {job.title}
          {job.year ? ` (${job.year})` : ""}
        </span>
        <Badge s={job.state} />
      </div>
      {ACTIVE.includes(job.state) && (
        <>
          <div className="minibar">
            <div className="fill" style={{ width: `${job.progress}%` }} />
          </div>
          <div className="job-meta muted">
            {job.progress}% {job.speed ? `· ${job.speed}` : ""} {job.eta ? `· ${job.eta}` : ""}
          </div>
        </>
      )}
      {job.state === "failed" && (
        <div className="job-meta">
          <span className="err">{(job.message || "hata").slice(0, 90)}</span>
          <button className="mini" onClick={() => onRetry(job.film_id)}>↻ retry</button>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [films, setFilms] = useState<Film[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState("");
  const [tab, setTab] = useState<"active" | "done" | "failed">("active");
  const [busy, setBusy] = useState<string | null>(null);

  const loadJobs = useCallback(() => api.jobs().then(setJobs), []);
  const refresh = useCallback(async () => {
    const [f, s, j] = await Promise.all([api.films(filter || undefined), api.stats(), api.jobs()]);
    setFilms(f);
    setStats(s);
    setJobs(j);
  }, [filter]);

  useEffect(() => { api.health().then(setHealth); }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const t = setInterval(loadJobs, 3000);
    return () => clearInterval(t);
  }, [loadJobs]);

  const run = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    try { await fn(); await refresh(); } finally { setBusy(null); }
  };

  const r = health?.radarr;
  const active = jobs.filter((j) => ACTIVE.includes(j.state));
  const done = jobs.filter((j) => j.state === "done");
  const failed = jobs.filter((j) => j.state === "failed");
  const shown = tab === "active" ? active : tab === "done" ? done : failed;

  return (
    <div className="wrap">
      <header>
        <h1>🎬 Youtubarr</h1>
        <span className="muted">
          {r?.configured
            ? r.ok ? `Radarr v${r.version} ✓` : `Radarr error`
            : "Radarr not set"}
        </span>
      </header>

      <div className="bar">
        <button disabled={!!busy} onClick={() => run("sync", api.sync)}>
          {busy === "sync" ? "…" : "↻ Sync"}
        </button>
        <button disabled={!!busy} onClick={() => run("search", api.searchAll)}>
          {busy === "search" ? "…" : "🔍 Search"}
        </button>
        <button className="ghost" disabled={!!busy} onClick={() => run("tmdb", api.tmdbSync)}>＋ TMDB</button>
        <button className="ghost" disabled={!!busy} onClick={() => run("chan", api.pollChannels)}>📡 Channels</button>
      </div>

      <div className="pills">
        {STATUSES.map((s) => (
          <span key={s} className={`pill ${filter === s ? "on" : ""}`}
                onClick={() => setFilter(filter === s ? "" : s)}>
            {s} <b>{stats[s] ?? 0}</b>
          </span>
        ))}
      </div>

      <div className="cards">
        {films.map((f) => (
          <div key={f.id} className="film">
            <div className="film-top">
              <span className="film-title">{f.original_title || f.title}{f.year ? ` (${f.year})` : ""}</span>
              <Badge s={f.status} />
            </div>
            <div className="film-meta muted">
              {f.runtime ? `${f.runtime} min` : ""}
              {f.match_score != null && <> · score <Confidence score={f.match_score} /></>}
            </div>
            {f.youtube_id && (
              <a className="film-yt" href={`https://youtu.be/${f.youtube_id}`} target="_blank" rel="noreferrer">
                ▶ {(f.youtube_title || "").slice(0, 50)} <span className="muted">{f.youtube_channel}</span>
              </a>
            )}
            <div className="film-actions">
              <button className="mini" onClick={() => api.searchOne(f.id).then(refresh)}>🔍 search</button>
              {f.youtube_id && <button className="mini" onClick={() => api.grab(f.id).then(refresh)}>⬇ grab</button>}
              {f.youtube_id && <button className="mini ghost" onClick={() => api.blocklist(f.id).then(refresh)}>✕</button>}
            </div>
          </div>
        ))}
        {films.length === 0 && <div className="muted empty">no films</div>}
      </div>

      <div className="queue">
        <div className="tabs">
          <button className={tab === "active" ? "tab on" : "tab"} onClick={() => setTab("active")}>
            Active <b>{active.length}</b>
          </button>
          <button className={tab === "done" ? "tab on" : "tab"} onClick={() => setTab("done")}>
            Done <b>{done.length}</b>
          </button>
          <button className={tab === "failed" ? "tab on" : "tab"} onClick={() => setTab("failed")}>
            Failed <b>{failed.length}</b>
          </button>
          <span className="spacer" />
          {tab === "done" && done.length > 0 && (
            <button className="mini ghost" onClick={() => api.clearJobs("done").then(loadJobs)}>clear done</button>
          )}
          {tab === "failed" && failed.length > 0 && (
            <button className="mini ghost" onClick={() => api.clearJobs("failed").then(loadJobs)}>clear failed</button>
          )}
        </div>
        <div className="jobs">
          {shown.map((j) => <JobCard key={j.id} job={j} onRetry={(id) => api.retry(id).then(loadJobs)} />)}
          {shown.length === 0 && <div className="muted empty">empty</div>}
        </div>
      </div>
    </div>
  );
}
