// Minimální, čistý frontend JS pro FastAPI backend
const API = window.location.origin || '';  // API základní URL

let currentUser = JSON.parse(localStorage.getItem('user') || 'null');  // Přihlášený uživatel
let selectedStarScore = 0;  // Vybrané hodnocení v modalu

const THEME_KEY = 'filmapp-theme';  // Klíč pro ukládání motivu v localStorage

function getStoredTheme() {
  try {
    const t = localStorage.getItem(THEME_KEY);  // Načíst motiv z pamětí
    return t === 'light' || t === 'dark' ? t : 'dark';  // Výchozí tmavý motiv
  } catch {
    return 'dark';
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);  // Aplikovat motiv do CSS
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
    btn.classList.toggle('is-light', theme === 'light');
  }
}

function initThemeToggle() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  applyTheme(getStoredTheme());  // Aplikovat uložený motiv
  btn.addEventListener('click', () => {
    const next = getStoredTheme() === 'dark' ? 'light' : 'dark';  // Přepnout motiv
    try {
      localStorage.setItem(THEME_KEY, next);  // Uložit nový motiv
    } catch {
      /* ignore */
    }
    applyTheme(next);
  });
}

function escapeHtml(text) {
  if (!text) return '';  // Ochrana před null
  return text.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);  // Bezpečné zakódování
}

function updateUserBar() {
  const el = document.getElementById('user-info'); if (!el) return;
  if (currentUser) {
    el.textContent = `👤 ${currentUser.username} (${currentUser.role})`;  // Zobrazit přihlášeného
    const logoutBtn = document.getElementById('logout-btn'); if (logoutBtn) logoutBtn.style.display = 'inline';
    const loginBtn = document.getElementById('login-btn'); if (loginBtn) loginBtn.style.display = 'none';
    const adminLink = document.getElementById('admin-link'); if (adminLink && currentUser.role === 'admin') adminLink.style.display = 'inline';  // Admin odkaz
  }
}
updateUserBar();

// Malá mapovací funkce pro opravy zobrazení žánrů
function normalizeGenre(name){
  if(!name) return name;
  if(name === 'Krimi') return 'Kriminal';  // Lokalizace názvu
  return name;
}

async function fetchJson(path, opts) {
  const res = await fetch(`${API}${path}`, opts);  // API volání
  let data;
  try {
    data = await res.json();  // Parsovat JSON
  } catch {
    throw new Error(`API request failed: ${res.status} ${res.statusText}`);
  }
  if (!res.ok) {  // Kontrola chyby
    throw new Error(data.detail || data.message || res.statusText || 'Chyba API');
  }
  return data;  // Vráti data
}

function renderFilms(gridId, films, append = false) {
  const grid = document.getElementById(gridId); if (!grid) return;  // Najít grid element
  if (!films || !films.length) { grid.innerHTML = "<p class='ui-soft'>Nic nenalezeno.</p>"; return; }  // Prázdný seznam
  const html = films.map(f => `
    <div class="film-card" onclick="openModal(${f.id})">
      <img src="${f.poster_url || ''}" alt="${f.title}" onerror="this.src='https://via.placeholder.com/180x270?text=No+Image'" />
      <div class="info">
        <div class="title">${f.title}</div>
  <div class="rating">⭐ ${(f.rating || 0).toFixed(1)} &nbsp; 📅 ${f.year || '?'}</div>
  ${f.status ? `<div style="margin-top:6px"><span class="badge">${f.status === 'want' ? 'Chci vidět' : f.status === 'seen' ? 'Viděl jsem' : f.status === 'fav' ? 'Oblíbené' : ''}</span></div>` : ''}
        ${f.trailer_key ? `<button class="btn btn-blue trailer-btn" onclick="event.stopPropagation(); openFullscreenTrailer('${f.trailer_key}')">▶ Sledujte trailer</button>` : ''}
      </div>
    </div>
  `).join('');
  if(append) grid.innerHTML += html; else grid.innerHTML = html;  // Přidat nebo nahradit
}

// Stav stránkování - pamatujeme si poslední dotaz
let currentPage = 1;
let lastQuery = null; // { urlBase, params }

async function resetAndLoadFilms(){
  currentPage = 1;  // Reset na první stránku
  await loadFilms(true);  // Znovu načíst filmy
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

async function loadFilms(forceReset = false) {
  const year = document.getElementById('f-year')?.value;
  const rating = document.getElementById('f-rating')?.value;
  const genre = document.getElementById('f-genre')?.value;
  const sort = document.getElementById('f-sort')?.value || 'rating';
  const searchRaw = document.getElementById('f-search')?.value?.trim() || '';

  // If called with forceReset true, or filters changed, restart pagination
  if(forceReset) currentPage = 1;

  let url = `/films?sort=${sort}&page=${currentPage}`;
  if (year) url += `&year=${year}`;
  if (genre) url += `&genre=${encodeURIComponent(genre)}`;
  if (rating !== undefined && rating !== null && rating !== '') {
    url += `&rating=${rating}`;
  }
  if (searchRaw) url += `&q=${encodeURIComponent(searchRaw)}`;
  // remember last query to allow loading next page
  lastQuery = { base: '/films', sort, year, genre, rating, q: searchRaw };

  try {
    const data = await fetchJson(url);
    if(currentPage === 1) renderFilms('films-grid', data);
    else renderFilms('films-grid', data, true);

    const loadMoreBtn = document.getElementById('load-more-btn');
    if(lastQuery && Array.isArray(data) && data.length === 20){
      loadMoreBtn.style.display = 'inline-block';
    } else {
      loadMoreBtn.style.display = 'none';
    }
  } catch (err) {
    const grid = document.getElementById('films-grid');
    if (grid) grid.innerHTML = `<p class="ui-error">Chyba: ${err.message}</p>`;
    const loadMoreBtn = document.getElementById('load-more-btn');
    if(loadMoreBtn) loadMoreBtn.style.display = 'none';
  }
}

// Attach load more button
document.addEventListener('DOMContentLoaded', ()=>{
  const lmb = document.getElementById('load-more-btn');
  if(lmb){
    lmb.addEventListener('click', async ()=>{
      if(!lastQuery) return;
      currentPage += 1;
      await loadFilms();
    });
  }
  const searchInp = document.getElementById('f-search');
  if (searchInp) {
    searchInp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        resetAndLoadFilms();
      }
    });
  }
});

async function loadTop10() { const data = await fetchJson('/films/top10'); renderFilms('top10-grid', data); }

async function loadTop10Filtered(){
  const genre = document.getElementById('top10-genre')?.value;
  const year = document.getElementById('top10-year')?.value;
  let url = '/films/top10';
  const params = [];
  if(genre) params.push(`genre=${encodeURIComponent(genre)}`);
  if(year) params.push(`year=${encodeURIComponent(year)}`);
  if(params.length) url += `?${params.join('&')}`;
  const data = await fetchJson(url);
  renderFilms('top10-grid', data);
}

async function loadWatchlist() { if (!currentUser) { alert('Musíš být přihlášen!'); return; } const data = await fetchJson(`/watchlist/${currentUser.id}`); renderFilms('watchlist-grid', data); }

async function randomFilm() { const film = await fetchJson('/films/random'); openModal(film.id); }

async function openModal(id) {
  const film = await fetchJson(`/films/${id}`);
  // determine user's current status for this film (if logged in)
  let filmStatus = null;
  if(currentUser){
    try{
      const wl = await fetchJson(`/watchlist/${currentUser.id}`);
      if(Array.isArray(wl)){
        const match = wl.find(i => i.id === id || i.id === film.id || i.film_id === id || i.film_id === film.id);
        if(match) filmStatus = match.status;
      }
    }catch(e){/* ignore */}
  }

  const body = document.getElementById('modal-body'); if (!body) return;
  const onWatchlistPage = !!document.getElementById('watchlist-grid');
  const userReview = currentUser ? (film.reviews || []).find(r => r.user_id === currentUser.id) : null;
  selectedStarScore = userReview ? userReview.score : 0;
  const reviewCards = (film.reviews || []).map(r => `
      <div class="review-item">
        <div class="review-header">
          <span class="review-score">★ ${r.score}/10</span>
          <span class="review-user">${escapeHtml(r.username)}</span>
          <span class="review-date">${new Date(r.updated_at).toLocaleDateString('cs-CZ')}</span>
        </div>
        <p>${r.comment ? escapeHtml(r.comment) : '<span class="ui-soft">Žádný komentář</span>'}</p>
      </div>
    `).join('');

  const statusLabel = filmStatus ? `Stav: ${filmStatus === 'want' ? 'Chci vidět' : filmStatus === 'seen' ? 'Viděl jsem' : filmStatus === 'fav' ? 'Oblíbené' : ''}` : 'Film není v seznamu.';

  body.innerHTML = `
    <img class="film-modal-poster" src="${film.poster_url||''}" alt="${film.title}" onerror="this.src='https://via.placeholder.com/200x300?text=No+Image'" />
    <div class="film-modal-info">
      <h2>${escapeHtml(film.title)}</h2>
      <p class="modal-subline">${film.year || ''} &nbsp; ⭐ ${(film.rating||0).toFixed(1)}</p>
      <div>${(film.genres||[]).map(g=>`<span class="badge">${normalizeGenre(g)}</span>`).join('')}</div>
      <p class="modal-desc">${escapeHtml(film.description||'')}</p>
      <div class="soundtrack-section">
        <h4>Soundtrack</h4>
        <div id="soundtrack-list"><p class="ui-soft">Načítám soundtrack...</p></div>
      </div>
      ${film.cast && film.cast.length ? `<div class="film-cast"><h4>Herecké obsazení</h4>${film.cast.slice(0,10).map(p => `<div class="cast-item"><strong>${escapeHtml(p.person_name)}</strong>${p.character ? ` jako ${escapeHtml(p.character)}` : ''}</div>`).join('')}</div>` : '<div class="film-cast"><h4>Herecké obsazení</h4><p class="ui-soft">Žádné herce jsme nenašli.</p></div>'}
      ${film.crew && film.crew.length ? `<div class="film-crew"><h4>Klíčový tým</h4>${film.crew.slice(0,8).map(p => `<div class="crew-item"><strong>${escapeHtml(p.person_name)}</strong>${p.job ? ` • ${escapeHtml(p.job)}` : ''}${p.department ? ` (${escapeHtml(p.department)})` : ''}</div>`).join('')}</div>` : ''}
      ${currentUser ? `
        <div class="watchlist-panel">
          <div id="modal-status-msg" style="margin-bottom:12px">${statusLabel}</div>
          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            <button class="btn wl-btn" data-status="want" onclick="event.stopPropagation(); updateWatchlistStatus(${film.id}, 'want')">Chci vidět</button>
            <button class="btn wl-btn" data-status="seen" onclick="event.stopPropagation(); updateWatchlistStatus(${film.id}, 'seen')">Viděl jsem</button>
            <button class="btn wl-btn" data-status="fav" onclick="event.stopPropagation(); updateWatchlistStatus(${film.id}, 'fav')">Oblíbené</button>
            <button class="btn btn-red wl-btn" data-status="none" onclick="event.stopPropagation(); updateWatchlistStatus(${film.id}, null)">Odebrat ze seznamu</button>
          </div>
        </div>
      ` : `<div class="ui-muted" style="margin-top:16px">Přihlas se pro stav filmu a správu seznamu.</div>`}
      <div class="rating-panel">
        ${film.community_rating ? `<div class="community-summary">Uživatelé: <strong>${film.community_rating.toFixed(1)}/10</strong> (${film.review_count} komentář${film.review_count === 1 ? '' : 'ů'})</div>` : `<div class="community-summary">Buď první, kdo ohodnotí tento film.</div>`}
        ${currentUser ? `
          <div class="rating-input">
            <div class="rating-label">Tvoje hodnocení:</div>
            <div class="stars" id="rating-stars">
              ${buildRatingStars(selectedStarScore)}
            </div>
            <textarea id="rating-comment" placeholder="Napiš komentář k hodnocení..." rows="4">${userReview ? escapeHtml(userReview.comment) : ''}</textarea>
            <button class="btn btn-blue" onclick="submitRating(${film.id})">Uložit komentář</button>
            <div id="rating-msg" class="rating-msg"></div>
          </div>
        ` : `<div class="ui-muted" style="margin-top:16px">Přihlas se pro hodnocení a komentáře.</div>`}
        ${reviewCards ? `<div class="review-list">${reviewCards}</div>` : ''}
      </div>
      ${film.trailer_key ? `<iframe width="100%" height="400" src="https://www.youtube.com/embed/${film.trailer_key}" frameborder="0" allowfullscreen></iframe>` : ''}
    </div>`;
  // set active state on buttons based on filmStatus
  setModalActiveStatus(filmStatus);
  if(filmStatus){
    const msg = document.getElementById('modal-status-msg'); if(msg) msg.textContent = `Stav: ${filmStatus === 'want' ? 'Chci vidět' : filmStatus === 'seen' ? 'Viděl jsem' : filmStatus === 'fav' ? 'Oblíbené' : ''}`;
  }
  initializeRatingStars(selectedStarScore);
  document.querySelectorAll('#rating-stars .star').forEach(star => {
    star.addEventListener('click', () => setRatingStars(star));
  });
  document.getElementById('modal').style.display = 'block';
  await loadSoundtrack(id);
}

async function loadSoundtrack(filmId) {
  const list = document.getElementById('soundtrack-list');
  if (!list) return;
  list.innerHTML = '<p class="ui-soft">Načítám soundtrack...</p>';
  try {
    const tracks = await fetchJson(`/films/${filmId}/soundtrack`);
    if (!Array.isArray(tracks) || tracks.length === 0) {
      list.innerHTML = '<p class="ui-soft">Soundtrack nenalezen.</p>';
      return;
    }
    list.innerHTML = tracks.map(track => {
      const title = escapeHtml(track.song_title || '');
      const artist = escapeHtml(track.artist || '');
      return `<div class="track-item">${title}${artist ? ` <span class="ui-muted">• ${artist}</span>` : ''}</div>`;
    }).join('');
  } catch (err) {
    list.innerHTML = '<p class="ui-error">Nepodařilo se načíst soundtrack.</p>';
  }
}

function buildRatingStars(current = 0) {
  let html = '';
  for (let i = 1; i <= 10; i++) {
    html += `<span class="star${i <= current ? ' active' : ''}" data-value="${i}" onclick="setRatingStars(this)">★</span>`;
  }
  return html;
}

function initializeRatingStars(score = 0) {
  selectedStarScore = score;
  const stars = document.querySelectorAll('#rating-stars .star');
  stars.forEach(s => {
    s.classList.toggle('active', Number(s.dataset.value) <= score);
  });
}

function setRatingStars(el) {
  const score = Number(el.dataset.value);
  if (!score) return;
  initializeRatingStars(score);
}

async function submitRating(filmId) {
  if (!currentUser) { alert('Musíš být přihlášen!'); return; }
  if (!selectedStarScore || selectedStarScore < 1 || selectedStarScore > 10) {
    alert('Vyber hodnocení 1 až 10 hvězdiček.');
    return;
  }
  const comment = document.getElementById('rating-comment')?.value || '';
  const resp = await fetch('/ratings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_id: currentUser.id, film_id: filmId, score: selectedStarScore, comment})
  });
  const data = await resp.json();
  const msg = document.getElementById('rating-msg');
  if (!resp.ok) {
    if (msg) {
      msg.textContent = data.detail || 'Chyba při ukládání hodnocení';
      msg.classList.remove('ui-success');
      msg.classList.add('ui-error');
    }
    return;
  }
  if (msg) { msg.textContent = data.message || 'Uloženo'; msg.classList.remove('ui-error'); msg.classList.add('ui-success'); }
  await openModal(filmId);
}

async function updateWatchlistStatus(filmId, status){
  if(!currentUser){ alert('Musíš být přihlášen!'); return; }
  const resp = await fetch('/watchlist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_id: currentUser.id, film_id: filmId, status})});
  if(!resp.ok){ alert('Chyba při ukládání stavu'); return; }
  // update modal UI immediately
  const msg = document.getElementById('modal-status-msg');
  if(status === null){ if(msg) msg.textContent = 'Odebráno ze seznamu'; setModalActiveStatus(null); }
  else { if(msg) msg.textContent = `Stav: ${status === 'want' ? 'Chci vidět' : status === 'seen' ? 'Viděl jsem' : 'Oblíbené'}`; setModalActiveStatus(status); }
  // refresh lists on page
  if(document.getElementById('watchlist-grid')) await loadWatchlist();
  if(document.getElementById('films-grid')) await loadFilms(true);
}

function setModalActiveStatus(status){
  // toggle active class on modal buttons
  const btns = document.querySelectorAll('#modal .wl-btn');
  btns.forEach(b => {
    const s = b.getAttribute('data-status');
    if(status === null){ b.classList.remove('btn-active'); }
    else if(s === status) b.classList.add('btn-active');
    else b.classList.remove('btn-active');
  });
}

function closeModal(e){ if (e.target.id === 'modal') document.getElementById('modal').style.display = 'none'; }

async function login(){ const u = document.getElementById('l-user')?.value; const p = document.getElementById('l-pass')?.value; const resp = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})}); const data = await resp.json(); if (resp.ok){ currentUser = data; localStorage.setItem('user', JSON.stringify(data)); updateUserBar(); window.location = '/'; } else { const m = document.getElementById('auth-msg'); if(m) m.textContent = data.detail || data.error; } }

async function register(){ const u = document.getElementById('r-user')?.value; const p = document.getElementById('r-pass')?.value; const resp = await fetch('/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})}); const data = await resp.json(); const m = document.getElementById('auth-msg'); if(m) m.textContent = data.message || data.detail || data.error; }

function logout(){ currentUser = null; localStorage.removeItem('user'); const ui = document.getElementById('user-info'); if(ui) ui.textContent='Nepřihlášen'; const lb = document.getElementById('logout-btn'); if(lb) lb.style.display='none'; const lbtn = document.getElementById('login-btn'); if(lbtn) lbtn.style.display='inline'; const al = document.getElementById('admin-link'); if(al) al.style.display='none'; window.location='/'; }

async function loadAdmin(){ if(!currentUser || currentUser.role!=='admin'){ alert('Nemáš přístup!'); return;} const users = await fetchJson('/admin/users'); const container = document.getElementById('admin-users'); if(!container) return; container.innerHTML = users.map(u=>`<div class="admin-user-row"><span>${u.username} (${u.role})</span>${u.banned?'<span class="banned-tag">BANNED</span>':''}${u.role!=='admin'?`<button class="btn btn-red" onclick="banUser(${u.id}, ${!u.banned})">${u.banned? 'Odblokovat' : 'Zablokovat'}</button>`:''}</div>`).join(''); }

async function banUser(userId, ban){ await fetch(`/admin/ban/${userId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ban})}); loadAdmin(); }

async function adminAddFilm(){ const title = document.getElementById('a-title')?.value; const year = parseInt(document.getElementById('a-year')?.value); const desc = document.getElementById('a-desc')?.value; const ratingInput = document.getElementById('a-rating')?.value; const rating = ratingInput === '' ? 0 : Number(ratingInput); if (!Number.isInteger(rating) || rating < 0 || rating > 10) { alert('Hodnocení musí být celé číslo od 0 do 10.'); return; } await fetch('/admin/films', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title, year, description: desc, rating})}); alert('Film přidán!'); }

document.addEventListener('DOMContentLoaded', ()=>{
  initThemeToggle();
  fetchJson('/genres').then(gs=>{ const sel = document.getElementById('f-genre'); if(sel) gs.forEach(g=> sel.innerHTML += `<option value="${g.name}">${normalizeGenre(g.name)}</option>`); });
  // Populate year select from backend stats (years with counts)
  fetchJson('/stats').then(s=>{
    const ys = s.by_year || [];
    const ysel = document.getElementById('f-year');
    if(ysel && Array.isArray(ys)){
      ys.forEach(y => {
        if(y.year){
          ysel.innerHTML += `<option value="${y.year}">${y.year} (${y.count})</option>`;
        }
      });
    }
  }).catch(()=>{/* ignore */});
  // Populate top10 filters too
  fetchJson('/genres').then(gs=>{ const sel = document.getElementById('top10-genre'); if(sel) gs.forEach(g=> sel.innerHTML += `<option value="${g.name}">${normalizeGenre(g.name)}</option>`); });
  fetchJson('/stats').then(s=>{ const ys = s.by_year || []; const tsel = document.getElementById('top10-year'); if(tsel && Array.isArray(ys)) ys.forEach(y=>{ if(y.year) tsel.innerHTML += `<option value="${y.year}">${y.year} (${y.count})</option>`; }); }).catch(()=>{/* ignore */});
  if(document.getElementById('top10-grid')) loadTop10();
  if(document.getElementById('films-grid')) loadFilms();
  if(document.getElementById('watchlist-grid')) loadWatchlist();
  if(document.getElementById('admin-users')) loadAdmin();
});
