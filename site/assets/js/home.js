// Home page: model cards from models.json (written by the brickkit viewer export).
import { initSite, $, esc, fmtInt, fmtCm, plural, getJSON, hash, Media, statusBadge, noticeFor, renderNotices } from './site.js';
import { icon } from './icons.js';

initSite();

const modelUrl = (slug) => `/m/${encodeURIComponent(slug)}/`;

function card(m, media) {
  const b = statusBadge(m.status);
  const h = fmtCm(m.dims_mm?.[1] || 0);
  const nv = (m.variants || []).length;
  const thumb = m.thumbnail ? media.image(m.thumbnail, 'sm') : '';
  const info = m.thumbnail ? media.imageInfo(m.thumbnail) : null;
  return `<a class="model-card" href="${modelUrl(m.slug)}">
    <div class="thumb">
      ${thumb ? `<img src="${thumb}" alt="${esc(m.name)}, rendered" loading="lazy" decoding="async" width="${info?.w || 800}" height="${info?.h || 800}">` : ''}
      <span class="badge ${b.cls}">${icon(b.icon)}${esc(b.text)}</span>
    </div>
    <div class="body">
      <div class="card-title"><h3>${esc(m.name)}</h3><span class="arrow" aria-hidden="true">${icon('arrowRight')}</span></div>
      ${m.description ? `<p class="desc">${esc(m.description)}</p>` : ''}
      <div class="meta">
        <span class="chip">${icon('brick')}${fmtInt(m.pieces ?? m.parts)} parts</span>
        <span class="chip">${icon('ruler')}${h} cm tall</span>
        <span class="chip">${icon('palette')}${plural(nv || 1, 'colourway')}</span>
      </div>
    </div>
  </a>`;
}

function hero(m, media) {
  if (!m?.thumbnail) return;
  const img = media.image(m.thumbnail, 'lg');
  $('#hero-art').innerHTML = `
    <a class="hero-card" href="${modelUrl(m.slug)}">
      <div class="hero-image">
        <img src="${img}" alt="${esc(m.name)}, rendered" width="1000" height="1000" fetchpriority="high">
        <div class="hero-image-top" aria-hidden="true"><span>In the spotlight</span><span>01 / Collection</span></div>
      </div>
      <div class="hero-card-label">
        <div><p class="featured-label">Featured model</p><h2>${esc(m.name)}</h2><p class="hero-specs">${fmtInt(m.pieces ?? m.parts)} parts <span aria-hidden="true">·</span> ${fmtCm(m.dims_mm?.[1] || 0)} cm tall</p></div>
        <span class="go" aria-hidden="true">${icon('arrowRight')}</span>
      </div>
    </a>`;
}

async function main() {
  const grid = $('#model-grid');
  let index;
  try {
    index = await getJSON('/models.json');
  } catch (e) {
    grid.innerHTML = '<p>Models could not be loaded right now. Please try again later.</p>';
    return;
  }
  const [media, conf] = await Promise.all([getJSON('/assets/media.json', { optional: true }), getJSON('/site.json', { optional: true })]);
  const models = index.models || [];
  const mediaFor = (m) => new Media(media, m.slug, hash(JSON.stringify(m)));
  grid.innerHTML = models.map((m) => card(m, mediaFor(m))).join('');
  $('#collection-count').textContent = `${String(models.length).padStart(2, '0')} original ${models.length === 1 ? 'design' : 'designs'}`;
  if (models.length) hero(models[0], mediaFor(models[0]));
  renderNotices(models.map((m) => noticeFor(m.slug, m, conf)));
}

main();
