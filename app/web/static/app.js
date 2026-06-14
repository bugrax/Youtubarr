const $ = s => document.querySelector(s);
async function api(path, method='GET'){ const r=await fetch(path,{method}); return r.json(); }
function badge(s){ return `<span class="badge ${s}">${s}</span>`; }

async function health(){
  const h=await api('/api/health');
  const r=h.radarr||{};
  $('#health').textContent = r.configured ? (r.ok?`Radarr v${r.version} bağlı ✓`:`Radarr HATA: ${r.error}`) : 'Radarr ayarlı değil';
}
async function stats(){
  const s=await api('/api/stats');
  $('#stats').textContent = Object.entries(s).map(([k,v])=>`${k}:${v}`).join('  ');
}
async function loadFilms(){
  stats();
  const films=await api('/api/films');
  $('#films tbody').innerHTML = films.map(f=>`
    <tr>
      <td>${f.original_title||f.title}</td>
      <td>${f.year||''}</td>
      <td>${f.runtime||''}dk</td>
      <td>${badge(f.status)}</td>
      <td>${f.youtube_id?`<a href="https://youtu.be/${f.youtube_id}" target="_blank">${(f.youtube_title||'').slice(0,40)}</a><br><span class="muted">${f.youtube_channel||''}</span>`:'<span class="muted">—</span>'}</td>
      <td class="${f.match_score>=.75?'high':f.match_score>=.6?'medium':'low'}">${f.match_score??''}</td>
      <td>
        <button class="ghost" onclick="searchOne(${f.id})">🔍</button>
        ${f.youtube_id?`<button onclick="grab(${f.id})">⬇</button>`:''}
      </td>
    </tr>`).join('');
  loadJobs();
}
async function loadJobs(){
  const jobs=await api('/api/jobs');
  $('#jobs tbody').innerHTML = jobs.slice(0,20).map(j=>`
    <tr><td>#${j.film_id}</td><td>${badge(j.state)}</td>
    <td>${j.progress||0}%</td><td>${j.speed||''}</td><td>${j.eta||''}</td></tr>`).join('');
}
async function sync(){ await api('/api/sync','POST'); loadFilms(); }
async function searchAll(){ $('#stats').textContent='aranıyor…'; await api('/api/search','POST'); loadFilms(); }
async function searchOne(id){ await api(`/api/films/${id}/search`); loadFilms(); }
async function grab(id){ await api(`/api/films/${id}/grab`,'POST'); loadFilms(); }

health(); loadFilms();
setInterval(loadJobs, 3000);
