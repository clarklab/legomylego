// Videos page: every model's build video from models.json (written by the brickkit viewer
// export), playable in place; models whose video isn't rendered yet show a "coming soon" card.
import { initSite, $, $$, esc, fmtInt, fmtBytes, getJSON, hash, Media, noticeFor, renderNotices } from './site.js';
import { icon } from './icons.js';

initSite();

const modelUrl = (slug) => `/m/${encodeURIComponent(slug)}/`;

function card(m, media) {
  const poster = m.poster || m.thumbnail;
  const posterUrl = poster ? media.image(poster, 'lg') : '';
  const meta = `<span class="chip">${icon('brick')}${fmtInt(m.pieces ?? m.parts)} parts</span>`;
  if (!m.video) {
    return `<article class="video-card soon">
      <div class="frame">${posterUrl ? `<img src="${posterUrl}" alt="${esc(m.name)}, rendered" loading="lazy" decoding="async">` : ''}
        <span class="soon-tag">${icon('film')}Video coming soon</span></div>
      <div class="body"><h2>${esc(m.name)}</h2>${m.description ? `<p class="desc">${esc(m.description)}</p>` : ''}
        <div class="meta">${meta}<a class="more" href="${modelUrl(m.slug)}">Open the model ${icon('arrowRight')}</a></div></div>
    </article>`;
  }
  const size = media.size(m.video);
  return `<article class="video-card">
    <div class="frame"><video controls playsinline preload="none" ${posterUrl ? `poster="${posterUrl}"` : ''} aria-label="${esc(m.name)} build video">
      <source src="${media.url(m.video)}" type="video/mp4"></video></div>
    <div class="body"><h2>${esc(m.name)}</h2>${m.description ? `<p class="desc">${esc(m.description)}</p>` : ''}
      <div class="meta">${meta}<a class="chip" href="${media.url(m.video)}" download="${esc(m.slug)}.mp4">${icon('download')}MP4${size ? ` · ${fmtBytes(size)}` : ''}</a>
        <a class="more" href="${modelUrl(m.slug)}">Open the model ${icon('arrowRight')}</a></div></div>
  </article>`;
}

async function main() {
  const grid = $('#video-grid');
  let index;
  try {
    index = await getJSON('/models.json');
  } catch (e) {
    grid.innerHTML = '<p>Videos could not be loaded right now. Please try again later.</p>';
    return;
  }
  const [media, conf] = await Promise.all([getJSON('/assets/media.json', { optional: true }), getJSON('/site.json', { optional: true })]);
  const models = (index.models || []).slice().sort((a, b) => Number(!a.video) - Number(!b.video));
  grid.innerHTML = models.map((m) => card(m, new Media(media, m.slug, hash(JSON.stringify(m))))).join('');
  // one video at a time
  const videos = $$('video', grid);
  videos.forEach((v) => v.addEventListener('play', () => videos.forEach((o) => { if (o !== v) o.pause(); })));
  renderNotices(models.map((m) => noticeFor(m.slug, m, conf)));
}

main();
