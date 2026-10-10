import { initSite, $, $$, esc, fmtInt, getJSON } from './site.js';
import { icon } from './icons.js';
import { brands } from './brands.js';

initSite();
const grid = $('#quick-grid');
const viewButtons = $$('[data-view]', $('.quick-view-switch'));
const storageKey = 'quick-bricks-view';
const brandBar = $('#quick-brands');
let observer;
let models = [];
let theme = '';

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

// The logo cards: one for each theme that has a build. A click shows that theme's builds only;
// a click on the card that is on shows them all again. ?theme=pokemon opens the page that way.
function showTheme(id, push = true) {
  const brand = brands.find(b => b.id === id && models.some(m => (m.brands || []).includes(b.id)));
  theme = brand ? brand.id : '';
  let shown = 0;
  $$('.quick-card', grid).forEach(card => {
    const m = models.find(x => x.slug === card.dataset.slug);
    const on = !theme || (m.brands || []).includes(theme);
    card.hidden = !on;
    shown += on;
    if (!on) $('video', card)?.pause();
  });
  $$('button', brandBar).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.brand === theme)));
  const builds = `${shown === 1 ? 'build' : 'builds'}`;
  const count = $('#quick-count');
  count.textContent = theme ? `${fmtInt(shown)} ${brand.name} ${builds}` : `${fmtInt(shown)} little ${builds} to make your own`;
  if (theme) {
    const all = document.createElement('button');
    all.type = 'button';
    all.className = 'quick-show-all';
    all.textContent = 'Show all';
    all.addEventListener('click', () => showTheme(''));
    count.append(' ', all);
  }
  if (push) {
    const url = new URL(location.href);
    theme ? url.searchParams.set('theme', theme) : url.searchParams.delete('theme');
    history.replaceState(null, '', url);
  }
}

function initBrands() {
  const have = brands.filter(b => models.some(m => (m.brands || []).includes(b.id)));
  brandBar.hidden = !have.length;
  const cols = have.length <= 3 ? have.length : Math.ceil(have.length / 2);   // two rows
  brandBar.style.setProperty('--cols', cols);
  brandBar.toggleAttribute('data-wide', cols > 3);
  brandBar.innerHTML = have.map(b => `<button type="button" class="quick-brand" data-brand="${esc(b.id)}" aria-pressed="false" style="--w:${b.w};--h:${b.h}" title="${esc(b.name)}"><span class="visually-hidden">${esc(b.name)}</span>${b.svg}</button>`).join('');
  $$('svg', brandBar).forEach(s => { s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false'); });
  $$('button', brandBar).forEach(b => b.addEventListener('click', () => showTheme(b.dataset.brand === theme ? '' : b.dataset.brand)));
}

async function main() {
  grid.setAttribute('aria-busy', 'true');
  try {
    const data = await getJSON('/quick/models.json');
    models = (data.models || []).slice().sort((a, b) => Number(!a.video) - Number(!b.video));
    grid.innerHTML = models.length ? models.map(card).join('') : '<p class="quick-message">More little builds are on the way. <a href="/#models">Explore our models</a> in the meantime.</p>';
    initPlayers();
    initBrands();
    showTheme(new URLSearchParams(location.search).get('theme') || '', false);
  } catch {
    $('#quick-count').textContent = 'The collection is taking a moment.';
    grid.innerHTML = '<div class="quick-message"><p>We couldn’t load the builds. Please try again.</p><button type="button" class="btn btn-ghost" id="quick-retry">Try again</button></div>';
    $('#quick-retry').addEventListener('click', main);
  } finally { grid.setAttribute('aria-busy', 'false'); }
}
main();
