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

const speaker = muted => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/>${muted ? '<path d="m16 9 6 6m0-6-6 6"/>' : '<path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>'}</svg>`;

function card(m) {
  const title = esc(m.name);
  const url = esc(m.url);
  const poster = m.poster ? `poster="${esc(m.poster)}"` : '';
  const media = m.video ? `<video playsinline muted loop preload="none" ${poster} data-src="${esc(m.video)}" aria-label="${title} build video"></video>
    <div class="quick-media-label">Watch the build</div>
    <div class="quick-video-controls">
      <button type="button" class="quick-play" aria-label="Play ${title} video">${icon('play')}</button>
      <button type="button" class="quick-sound" aria-label="Unmute ${title} video" aria-pressed="false">${speaker(true)}</button>
    </div><progress class="quick-progress" max="1" value="0" aria-label="Video progress"></progress>`
    : `${m.poster ? `<img src="${esc(m.poster)}" alt="${title} built from LEGO bricks" loading="lazy" decoding="async">` : ''}<div class="quick-media-label">Build preview</div>`;
  return `<article class="quick-card" data-slug="${esc(m.slug)}">
    <div class="quick-media${m.video ? '' : ' is-still'}">${media}</div>
    <div class="quick-card-info"><h2><a href="${url}">${title}</a></h2><p class="quick-piece-count">${fmtInt(m.pieces)} pieces</p></div>
    <a class="quick-instructions" href="${url}"><span>View instructions<span class="visually-hidden"> for ${title}</span></span>${icon('arrowRight')}</a>
  </article>`;
}

function initPlayers() {
  const videos = $$('video', grid);
  const load = v => { if (!v.getAttribute('src')) { v.src = v.dataset.src; v.load(); } };
  videos.forEach(v => {
    const frame = v.parentElement;
    const play = $('.quick-play', frame);
    const sound = $('.quick-sound', frame);
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
    sound.addEventListener('click', () => {
      v.muted = !v.muted;
      sound.innerHTML = speaker(v.muted);
      sound.setAttribute('aria-pressed', String(!v.muted));
      sound.setAttribute('aria-label', `${v.muted ? 'Unmute' : 'Mute'} ${name} video`);
    });
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
