import { initSite, $, $$, esc, fmtInt, getJSON } from './site.js';
import { icon } from './icons.js';

initSite();
const grid = $('#quick-grid');
const viewButtons = $$('[data-view]', $('.quick-view-switch'));
const storageKey = 'quick-bricks-view';
let observer;

function setView(view, save = false) {
  view = view === 'single' ? 'single' : 'grid';
  grid.dataset.view = view;
  viewButtons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
  if (save) { try { localStorage.setItem(storageKey, view); } catch { /* storage is optional */ } }
}
try { setView(localStorage.getItem(storageKey)); } catch { setView('grid'); }
viewButtons.forEach(b => b.addEventListener('click', () => setView(b.dataset.view, true)));

function card(m) {
  const title = esc(m.name);
  const url = esc(m.url);
  const poster = m.poster ? `poster="${esc(m.poster)}"` : '';
  const media = m.video ? `<video playsinline muted loop preload="none" ${poster} data-src="${esc(m.video)}" aria-label="${title} build video"></video>`
    : (m.poster ? `<img src="${esc(m.poster)}" alt="${title} built from LEGO bricks" loading="lazy" decoding="async">` : '');
  const controls = m.video ? `<div class="quick-video-controls">
      <button type="button" class="quick-play" aria-label="Play ${title} video">${icon('play')}</button>
    </div><progress class="quick-progress" max="1" value="0" aria-label="Video progress"></progress>` : '';
  return `<article class="quick-card" data-slug="${esc(m.slug)}">
    <div class="quick-media${m.video ? '' : ' is-still'}">${media}
      <div class="quick-card-info"><h2><a href="${url}">${title}</a></h2><p class="quick-piece-count">${icon('brick')}${fmtInt(m.pieces)}<span class="visually-hidden"> pieces</span></p></div>
      ${controls}
    </div>
    <a class="quick-instructions" href="${url}"><span>View Instructions<span class="visually-hidden"> for ${title}</span></span>${icon('arrowRight')}</a>
  </article>`;
}

function initPlayers() {
  const videos = $$('video', grid);
  const load = v => { if (!v.getAttribute('src')) { v.src = v.dataset.src; v.load(); } };
  videos.forEach(v => {
    const frame = v.parentElement;
    const play = $('.quick-play', frame);
    const name = v.getAttribute('aria-label').replace(/ build video$/, '');
    const sync = () => {
      play.innerHTML = icon(v.paused ? 'play' : 'pause');
      play.setAttribute('aria-label', `${v.paused ? 'Play' : 'Pause'} ${name} video`);
    };
    const failure = () => {
      if (!$('.quick-video-error', frame)) {
        const message = document.createElement('p');
        message.className = 'quick-video-error';
        message.setAttribute('role', 'status');
        message.textContent = 'The video could not play. Your building instructions are still available below.';
        frame.append(message);
      }
      sync();
    };
    const toggle = async () => {
      if (!v.paused) { v.pause(); return; }
      load(v);
      try { await v.play(); $('.quick-video-error', frame)?.remove(); } catch { failure(); }
    };
    play.addEventListener('click', toggle);
    v.addEventListener('click', toggle);
    v.addEventListener('play', () => { videos.forEach(other => { if (v !== other) other.pause(); }); sync(); });
    v.addEventListener('pause', sync);
    v.addEventListener('error', failure);
    v.addEventListener('timeupdate', () => { $('.quick-progress', frame).value = v.duration ? v.currentTime / v.duration : 0; });
  });
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => entries.forEach(e => {
      if (!e.isIntersecting) e.target.pause();
    }), { threshold: .15 });
    videos.forEach(v => observer.observe(v));
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) videos.forEach(v => v.pause()); });
}

async function main() {
  grid.setAttribute('aria-busy', 'true');
  try {
    const data = await getJSON('/quick/models.json');
    const models = (data.models || []).slice().sort((a, b) => Number(!a.video) - Number(!b.video));
    $('#quick-count').textContent = `${fmtInt(models.length)} little ${models.length === 1 ? 'build' : 'builds'} to make your own`;
    grid.innerHTML = models.length ? models.map(card).join('') : '<p class="quick-message">More little builds are on the way. <a href="/#models">Explore our models</a> in the meantime.</p>';
    initPlayers();
  } catch {
    $('#quick-count').textContent = 'The collection is taking a moment.';
    grid.innerHTML = '<div class="quick-message"><p>We couldn’t load the builds. Please try again.</p><button type="button" class="btn btn-ghost" id="quick-retry">Try again</button></div>';
    $('#quick-retry').addEventListener('click', main);
  } finally { grid.setAttribute('aria-busy', 'false'); }
}
main();
