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
      <h3>${esc(m.name)}</h3>
      ${m.description ? `<p class="desc">${esc(m.description)}</p>` : ''}
      <div class="meta">
        <span class="chip">${icon('brick')}${fmtInt(m.pieces ?? m.parts)} parts</span>
        <span class="chip">${icon('ruler')}${h} cm tall</span>
        <span class="chip">${icon('palette')}${plural(nv || 1, 'colourway')}</span>
      </div>
    </div>
    <span class="arrow" aria-hidden="true">${icon('arrowRight')}</span>
  </a>`;
}

const SOON = `<div class="model-card soon" role="note">
  <div class="soon-bricks" aria-hidden="true"><span style="background:#eb152c"></span><span style="background:#fedb05"></span><span style="background:#1f6fd1"></span></div>
  <h3>More models on the drawing board</h3>
  <p>New builds show up here once every check passes.</p>
</div>`;

function hero(m, media) {
  if (!m?.thumbnail) return;
  const b = statusBadge(m.status);
  const img = media.image(m.thumbnail, 'lg');
  $('#hero-art').innerHTML = `
    <span class="sticker sticker-parts" aria-hidden="true"><span><b>${fmtInt(m.pieces ?? m.parts)}</b><small>REAL PARTS</small></span></span>
    ${m.status === 'pass' ? `<span class="sticker sticker-check" aria-hidden="true">${icon('checkCircle')}${esc(b.text)}</span>` : ''}
    <a class="hero-card" href="${modelUrl(m.slug)}">
      <img src="${img}" alt="${esc(m.name)}, rendered" width="800" height="800" fetchpriority="high">
      <span class="hero-card-label"><span><strong>${esc(m.name)}</strong><br><span>${fmtInt(m.pieces ?? m.parts)} parts · ${fmtCm(m.dims_mm?.[1] || 0)} cm tall</span></span><span class="go">${icon('arrowRight')}</span></span>
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
  grid.innerHTML = models.map((m) => card(m, mediaFor(m))).join('') + SOON;
  if (models.length) hero(models[0], mediaFor(models[0]));
  renderNotices(models.map((m) => noticeFor(m.slug, m, conf)));
}

main();
