// Minimal, clean frontend JS for FastAPI backend
const API = '';

let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

function updateUserBar() {
  const el = document.getElementById('user-info'); if (!el) return;
  if (currentUser) {
    el.textContent = `👤 ${currentUser.username} (${currentUser.role})`;
    const logoutBtn = document.getElementById('logout-btn'); if (logoutBtn) logoutBtn.style.display = 'inline';
    const loginBtn = document.getElementById('login-btn'); if (loginBtn) loginBtn.style.display = 'none';
    const adminLink = document.getElementById('admin-link'); if (adminLink && currentUser.role === 'admin') adminLink.style.display = 'inline';
  }
}
updateUserBar();

async function fetchJson(path, opts) { const res = await fetch(`${API}${path}`, opts); return res.json(); }

function renderFilms(gridId, films) {
  const grid = document.getElementById(gridId); if (!grid) return;
  if (!films || !films.length) { grid.innerHTML = "<p style='color:#888'>Žádné filmy nenalezeny.</p>"; return; }
  grid.innerHTML = films.map(f => `
    <div class="film-card" onclick="openModal(${f.id})">
      <img src="${f.poster_url || ''}" alt="${f.title}" onerror="this.src='https://via.placeholder.com/180x270?text=No+Image'" />
      <div class="info">
        <div class="title">${f.title}</div>
        <div class="rating">⭐ ${(f.rating || 0).toFixed(1)} &nbsp; 📅 ${f.year || '?'}</div>
        ${f.trailer_key ? `<button class="btn btn-blue trailer-btn" onclick="event.stopPropagation(); openFullscreenTrailer('${f.trailer_key}')">▶ Sledujte trailer</button>` : ''}
      </div>
    </div>
  `).join('');
}

function openFullscreenTrailer(key) {
  const overlay = document.getElementById('fullscreen-trailer');
  overlay.innerHTML = `
    <div class="fullscreen-content">
      <button class="close-btn" onclick="closeFullscreenTrailer()">✕</button>
      <iframe
        width="100%"
        height="100%"
        src="https://www.youtube.com/embed/${key}?autoplay=1"
        title="YouTube trailer"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen>
      </iframe>
    </div>
  `;
  overlay.style.display = 'flex';
  document.addEventListener('keydown', handleEsc);
}

function closeFullscreenTrailer() {
  const overlay = document.getElementById('fullscreen-trailer');
  overlay.innerHTML = '';
  overlay.style.display = 'none';
  document.removeEventListener('keydown', handleEsc);
}

function handleEsc(e) {
  if (e.key === 'Escape') {
    closeFullscreenTrailer();
  }
}

async function loadFilms() {
  const year = document.getElementById('f-year')?.value;
  const rating = document.getElementById('f-rating')?.value;
  const genre = document.getElementById('f-genre')?.value;
  const sort = document.getElementById('f-sort')?.value || 'rating';
  let url = `/films?sort=${sort}`;
  if (year) url += `&year=${year}`;
  if (rating) url += `&min_rating=${rating}`;
  if (genre) url += `&genre=${encodeURIComponent(genre)}`;
  const data = await fetchJson(url);
  renderFilms('films-grid', data);
}

async function loadTop10() { const data = await fetchJson('/films/top10'); renderFilms('top10-grid', data); }

async function loadWatchlist() { if (!currentUser) { alert('Musíš být přihlášen!'); return; } const data = await fetchJson(`/watchlist/${currentUser.id}`); renderFilms('watchlist-grid', data); }

async function moodMatch() { const mood = document.getElementById('mood-input')?.value; if (!mood) return; const data = await fetchJson('/mood-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({mood}) }); renderFilms('mood-grid', data); }

async function randomFilm() { const film = await fetchJson('/films/random'); openModal(film.id); }

async function openModal(id) {
  const film = await fetchJson(`/films/${id}`);
  const body = document.getElementById('modal-body'); if (!body) return;
  body.innerHTML = `
    <img src="${film.poster_url||''}" alt="${film.title}" onerror="this.src='https://via.placeholder.com/200x300?text=No+Image'" />
    <div style="flex:1">
      <h2>${film.title}</h2>
      <p style="color:#aaa;margin:6px 0">${film.year || ''} &nbsp; ⭐ ${(film.rating||0).toFixed(1)}</p>
      <div>${(film.genres||[]).map(g=>`<span class="badge">${g}</span>`).join('')}</div>
      <p style="margin-top:12px;font-size:.9rem;color:#ccc">${film.description||''}</p>
      ${film.czdb ? `<div style="margin-top:10px;padding:8px;background:#071b2b;border-radius:6px">
        <strong>CZDB:</strong>
        <div style="font-size:.95rem;margin-top:6px">${film.czdb.title || film.czdb.name || ''} ${film.czdb.year?`(${film.czdb.year})`:''}</div>
        ${film.czdb.rating?`<div>Hodnocení (CZDB): ${film.czdb.rating}</div>`:''}
        ${film.czdb.url?`<div><a href="${film.czdb.url}" target="_blank">Detail na CZDB</a></div>`:''}
      </div>` : ''}
    </div>`;
  document.getElementById('modal').style.display = 'block';
}

function closeModal(e){ if (e.target.id === 'modal') document.getElementById('modal').style.display = 'none'; }

async function login(){ const u = document.getElementById('l-user')?.value; const p = document.getElementById('l-pass')?.value; const resp = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})}); const data = await resp.json(); if (resp.ok){ currentUser = data; localStorage.setItem('user', JSON.stringify(data)); updateUserBar(); window.location = '/'; } else { const m = document.getElementById('auth-msg'); if(m) m.textContent = data.detail || data.error; } }

async function register(){ const u = document.getElementById('r-user')?.value; const p = document.getElementById('r-pass')?.value; const resp = await fetch('/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})}); const data = await resp.json(); const m = document.getElementById('auth-msg'); if(m) m.textContent = data.message || data.detail || data.error; }

function logout(){ currentUser = null; localStorage.removeItem('user'); const ui = document.getElementById('user-info'); if(ui) ui.textContent='Nepřihlášen'; const lb = document.getElementById('logout-btn'); if(lb) lb.style.display='none'; const lbtn = document.getElementById('login-btn'); if(lbtn) lbtn.style.display='inline'; const al = document.getElementById('admin-link'); if(al) al.style.display='none'; window.location='/'; }

async function loadAdmin(){ if(!currentUser || currentUser.role!=='admin'){ alert('Nemáš přístup!'); return;} const users = await fetchJson('/admin/users'); const container = document.getElementById('admin-users'); if(!container) return; container.innerHTML = users.map(u=>`<div style="background:#0f3460;padding:10px;border-radius:6px;margin:6px 0;display:flex;align-items:center;gap:12px"><span>${u.username} (${u.role})</span>${u.banned?'<span style="color:#e94560">BANNED</span>':''}${u.role!=='admin'?`<button class="btn btn-red" onclick="banUser(${u.id}, ${!u.banned})">${u.banned? 'Odblokovat' : 'Zablokovat'}</button>`:''}</div>`).join(''); }

async function banUser(userId, ban){ await fetch(`/admin/ban/${userId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ban})}); loadAdmin(); }

async function adminAddFilm(){ const title = document.getElementById('a-title')?.value; const year = parseInt(document.getElementById('a-year')?.value); const desc = document.getElementById('a-desc')?.value; const rating = parseFloat(document.getElementById('a-rating')?.value); await fetch('/admin/films', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title, year, description: desc, rating})}); alert('Film přidán!'); }

document.addEventListener('DOMContentLoaded', ()=>{
  fetchJson('/genres').then(gs=>{ const sel = document.getElementById('f-genre'); if(sel) gs.forEach(g=> sel.innerHTML += `<option value="${g.name}">${g.name}</option>`); });
  if(document.getElementById('top10-grid')) loadTop10();
  if(document.getElementById('films-grid')) loadFilms();
  if(document.getElementById('watchlist-grid')) loadWatchlist();
  if(document.getElementById('admin-users')) loadAdmin();
});
      if (name === "admin") loadAdmin();
