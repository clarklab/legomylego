// Model page: works for any model exported by `python -m brickkit viewer <slug>`.
import {
  initSite, $, $$, esc, fmtInt, fmtCm, fmtBytes, plural, humanize, getJSON, hash, Media,
  checkInfo, checkCounts, noticeFor, renderNotices, SITE,
} from './site.js';
import { icon } from './icons.js';

initSite();

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const state = { variant: 0, step: 0, viewer: null, data: null, media: null, byStep: [], colourByName: new Map() };

function getSlug() {
  const fromBody = document.body.dataset.slug;
  if (fromBody) return fromBody;
  const q = new URLSearchParams(location.search).get('m');
  if (q) return q;
  const m = location.pathname.match(/^\/m\/([^/]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

export function ledeFor(d) {
  if (d.description) return d.description;
  const h = fmtCm(d.dims_mm?.[1] || 0);
  let s = `${fmtInt(d.pieces ?? d.parts)} real LEGO parts, about ${h} cm tall`;
  const extras = [];
  if (d.mechanism) extras.push('a working mechanism');
  if (d.lights?.length) extras.push(d.lights.length === 1 ? 'a built-in light' : 'built-in lights');
  if (extras.length) s += `, with ${extras.join(' and ')}`;
  return `${s}. Every part, connection and step checked by computer.`;
}

function bestRender(renders = []) {
  return renders.find((r) => /hero/i.test(r)) || renders.find((r) => /three.?quarter/i.test(r)) || renders[0] || null;
}

function setMeta(d, slug) {
  const title = `${d.name}: buildable LEGO model | ${SITE.name}`;
  const desc = ledeFor(d);
  const url = `${SITE.url}/m/${encodeURIComponent(slug)}/`;
  document.title = title;
  const set = (sel, attr, val) => { const el = document.head.querySelector(sel); if (el) el.setAttribute(attr, val); };
  set('meta[name="description"]', 'content', desc);
  set('link[rel="canonical"]', 'href', url);
  set('meta[property="og:title"]', 'content', title);
  set('meta[property="og:description"]', 'content', desc);
  set('meta[property="og:url"]', 'content', url);
  set('meta[name="twitter:title"]', 'content', title);
  set('meta[name="twitter:description"]', 'content', desc);
  document.head.querySelector('meta[name="robots"]')?.remove();
}

function notFound(slug) {
  document.title = `Model not found | ${SITE.name}`;
  $('.stage').innerHTML = `
    <div class="nf" style="grid-column:1/-1">
      <div>
        <h1>Model not found</h1>
        <p>${slug ? `We couldn't find a model called “${esc(slug)}”.` : 'No model was chosen.'} It may still be on the drawing board.</p>
        <div class="cta"><a class="btn" href="/#models">${icon('arrowRight')}See all models</a></div>
      </div>
    </div>`;
}

// ---------- panel ----------

function renderTitle(d) {
  $$('[data-fill="name"]').forEach((el) => { el.textContent = d.name; });
  $('#model-lede').textContent = ledeFor(d);
}

function variantBom(k = state.variant) {
  return state.data.variants?.[k]?.bom || state.data.variants?.[0]?.bom || [];
}

function renderStats(d) {
  const [w, h, dp] = d.dims_mm || [0, 0, 0];
  const lots = variantBom().length;
  const stat = (ic, k, v, unit = '') => `<div class="stat"><div class="k">${icon(ic)}${k}</div><div class="v">${v}${unit ? `<small>${unit}</small>` : ''}</div></div>`;
  $('#stats').innerHTML =
    stat('brick', 'Parts', fmtInt(d.pieces ?? d.parts)) +
    stat('ruler', 'Height', fmtCm(h), 'cm') +
    stat('steps', 'Steps', fmtInt(d.steps?.length || 0)) +
    stat('list', 'Part types', fmtInt(lots));
  $('#size-line').textContent = `${fmtCm(w)} × ${fmtCm(dp)} × ${fmtCm(h)} cm (width × depth × height)`;
}

function topColours(bom, n = 4) {
  const by = new Map();
  for (const r of bom) by.set(r.colour, { hex: r.hex, qty: (by.get(r.colour)?.qty || 0) + r.qty });
  return [...by.entries()].sort((a, b) => b[1].qty - a[1].qty).slice(0, n).map(([name, v]) => ({ name, hex: v.hex }));
}

function renderColourways(d) {
  const vs = d.variants || [];
  if (!vs.length) return;
  $('#colourways-block').hidden = false;
  $('#colourways').innerHTML = vs.map((v, k) => {
    const dots = topColours(v.bom || []).map((c) => `<i style="background:${esc(c.hex)}" title="${esc(c.name)}"></i>`).join('');
    return `<button class="colourway" type="button" data-k="${k}" aria-pressed="${k === state.variant}"><span class="dots" aria-hidden="true">${dots}</span>${esc(v.title || humanize(v.name))}</button>`;
  }).join('');
  $('#colourway-current').textContent = vs[state.variant]?.title || '';
  $$('#colourways .colourway').forEach((b) => b.addEventListener('click', () => setVariant(Number(b.dataset.k))));
}

function setVariant(k) {
  if (k === state.variant) return;
  state.variant = k;
  $$('#colourways .colourway').forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.k) === k)));
  $('#colourway-current').textContent = state.data.variants[k]?.title || '';
  const url = new URL(location.href);
  if (k === 0) url.searchParams.delete('c'); else url.searchParams.set('c', state.data.variants[k].name);
  history.replaceState(null, '', url);
  state.viewer?.setVariant(k);
  renderStats(state.data);
  renderParts();
  renderDownloads();
  updateBuildUI(state.step);
  if (state.selected != null) showPartTip(state.selected);
}

function renderFeatures(d) {
  const f = [];
  if (d.mechanism) f.push(['gear', 'Working mechanism']);
  if (d.lights?.length) f.push(['bulb', d.lights.length === 1 ? 'Built-in light' : `${d.lights.length} built-in lights`]);
  if ((d.variants || []).length > 1) f.push(['palette', `${d.variants.length} colourways`]);
  if (d.files?.booklet) f.push(['book', 'Instructions']);
  const subs = new Set((d.steps || []).map((s) => s.submodel));
  if (subs.size > 1) f.push(['layers', plural(subs.size - 1, 'sub-assembly', 'sub-assemblies')]);
  if (!f.length) return;
  $('#features-block').hidden = false;
  $('#features').innerHTML = f.map(([ic, t]) => `<span class="chip">${icon(ic)}${esc(t)}</span>`).join('');
}

function checkSummaryText(c) {
  const bits = [];
  if (c.pass) bits.push(`${c.pass} passed`);
  if (c.warn) bits.push(plural(c.warn, 'note'));
  if (c.fail) bits.push(`${c.fail} failed`);
  return bits.join(' · ');
}

function renderCheckSummary(d) {
  const checks = d.checks || [];
  const el = $('#check-summary');
  if (!checks.length) return;
  const c = checkCounts(checks);
  const cls = c.fail ? 'fail' : c.warn ? 'warn' : '';
  const ic = c.fail ? 'xCircle' : 'shield';
  el.innerHTML = `<span class="ring ${cls}">${icon(ic)}</span><span><strong>Checked by computer</strong><span>${checkSummaryText(c)} · not build-tested yet</span></span><span class="chev">${icon('chevronRight')}</span>`;
  el.hidden = false;
  const badge = c.fail
    ? `<span class="badge badge-fail">${icon('xCircle')}${plural(c.fail, 'check')} failing</span>`
    : `<span class="badge badge-pass">${icon('checkCircle')}${c.warn ? `${checks.length - c.warn} of ${checks.length} checks pass` : `All ${checks.length} checks pass`}</span>`;
  $('#title-badges').innerHTML = badge + (c.warn ? `<span class="badge badge-warn">${icon('alert')}${plural(c.warn, 'note')}</span>` : '');
}

function renderCTA(d) {
  const f = d.files || {};
  const out = [];
  if (f.booklet) out.push(`<a class="btn btn-red" href="${state.media.url(f.booklet)}" target="_blank" rel="noopener">${icon('book')}Instructions</a>`);
  else out.push(`<a class="btn btn-red" href="#downloads">${icon('download')}Downloads</a>`);
  out.push(`<a class="btn btn-ghost" href="#parts">${icon('list')}Parts list</a>`);
  $('#panel-cta').innerHTML = out.join('');
}

// ---------- checks ----------

function renderChecks(d) {
  const checks = d.checks || [];
  if (!checks.length) return;
  $('#checks').hidden = false;
  const c = checkCounts(checks);
  $('#checks-intro').textContent = `brickkit tests the design before anyone builds it: ${checkSummaryText(c)}.`;
  const label = { pass: 'Pass', warn: 'Note', fail: 'Fail' };
  const bic = { pass: 'checkCircle', warn: 'alert', fail: 'xCircle' };
  $('#checks-grid').innerHTML = checks.map((k) => {
    const [title, what, ic] = checkInfo(k.name);
    const st = ['pass', 'warn', 'fail'].includes(k.status) ? k.status : 'unknown';
    return `<article class="check-card ${st}">
      <span class="ci">${icon(ic)}</span>
      <div class="head"><h3>${esc(title)}</h3><span class="badge badge-${st}">${icon(bic[st] || 'info')}${label[st] || humanize(k.status)}</span></div>
      ${what ? `<p class="what">${esc(what)}</p>` : ''}
      <p class="summary">${esc(k.summary || '')}</p>
      ${(k.details || []).length ? `<ul class="details">${k.details.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
    </article>`;
  }).join('');
}

// ---------- downloads ----------

function blobUrl(text, type) {
  return URL.createObjectURL(new Blob([text], { type }));
}

function bomFiles(bom) {
  const xml = '<INVENTORY>\n' + bom.filter((r) => r.bricklink_part).map((r) =>
    `<ITEM><ITEMTYPE>${esc(r.bricklink_type || 'P')}</ITEMTYPE><ITEMID>${esc(r.bricklink_part)}</ITEMID>${r.bricklink_colour != null && (r.bricklink_type || 'P') === 'P' ? `<COLOR>${r.bricklink_colour}</COLOR>` : ''}<MINQTY>${r.qty}</MINQTY></ITEM>`).join('\n') + '\n</INVENTORY>\n';
  const pab = 'elementId,quantity\n' + bom.filter((r) => r.element_id).map((r) => `${r.element_id},${r.qty}`).join('\n') + '\n';
  const q = (s) => (/[",\n]/.test(String(s ?? '')) ? `"${String(s).replace(/"/g, '""')}"` : String(s ?? ''));
  const csv = 'qty,part,name,colour,bricklink_part,bricklink_colour,element_id,rare\n' +
    bom.map((r) => [r.qty, r.part, r.name, r.colour, r.bricklink_part, r.bricklink_colour, r.element_id, r.rare ? 1 : 0].map(q).join(',')).join('\n') + '\n';
  return { xml, pab, csv };
}

let blobUrls = [];
function renderDownloads() {
  const d = state.data, f = d.files || {}, media = state.media;
  blobUrls.forEach((u) => URL.revokeObjectURL(u));
  blobUrls = [];
  const variant = d.variants?.[state.variant];
  const custom = state.variant !== 0 && variant;
  const slugName = d.slug || 'model';
  let bf = null;
  if (custom) bf = bomFiles(variant.bom || []);
  const item = (key, ic, title, desc, tone = '', opts = {}) => {
    const path = f[key];
    if (!path && !opts.href) {
      if (!opts.soon) return '';
      return `<div class="dl soon"><span class="di">${icon(ic)}</span><span><strong>${esc(title)}</strong><span>Coming soon</span></span><span></span></div>`;
    }
    const href = opts.href || media.url(path);
    const size = opts.size ?? (path ? media.size(path) : null);
    const dl = opts.newTab ? 'target="_blank" rel="noopener"' : `download="${esc(opts.filename || String(path).split('/').pop())}"`;
    return `<a class="dl ${tone}" href="${href}" ${dl}><span class="di">${icon(ic)}</span><span><strong>${esc(title)}</strong><span>${esc(desc)}</span></span><span class="go">${size ? `<span class="size">${fmtBytes(size)}</span>` : icon(opts.newTab ? 'external' : 'download')}</span></a>`;
  };
  const out = [];
  const vb = custom && variant.files?.booklet;
  out.push(vb
    ? item(null, 'book', 'Building instructions', `${variant.title}: step-by-step PDF, ${plural(d.steps?.length || 0, 'step')}`, 'red', { href: media.url(vb), size: media.size(vb), newTab: true })
    : item('booklet', 'book', 'Building instructions', `Step-by-step PDF, ${plural(d.steps?.length || 0, 'step')}`, 'red', { soon: true, newTab: true }));
  out.push(item('video', 'film', 'Build video', 'Watch it come together (MP4)', 'red', { soon: true }));
  out.push(item('mpd', 'cube', 'LDraw model (.mpd)', 'Opens in BrickLink Studio, LeoCAD or LDCad', 'dark'));
  if (custom) {
    const push = (u) => { blobUrls.push(u); return u; };
    const vslug = `${slugName}_${variant.name}`;
    out.push(item(null, 'tag', 'BrickLink wanted list (.xml)', `${variant.title}: upload to BrickLink to buy every part`, '', { href: push(blobUrl(bf.xml, 'application/xml')), filename: `${vslug}_bricklink_wanted.xml`, size: bf.xml.length }));
    out.push(item(null, 'cart', 'Pick a Brick list (.csv)', `${variant.title}: LEGO element IDs and quantities`, '', { href: push(blobUrl(bf.pab, 'text/csv')), filename: `${vslug}_pick_a_brick.csv`, size: bf.pab.length }));
    out.push(item(null, 'list', 'Parts list (.csv)', `${variant.title}: every part, colour and quantity`, '', { href: push(blobUrl(bf.csv, 'text/csv')), filename: `${vslug}_parts.csv`, size: bf.csv.length }));
  } else {
    out.push(item('bricklink_xml', 'tag', 'BrickLink wanted list (.xml)', 'Upload to BrickLink to buy every part'));
    out.push(item('pick_a_brick_csv', 'cart', 'Pick a Brick list (.csv)', 'LEGO element IDs and quantities'));
    out.push(item('parts_csv', 'list', 'Parts list (.csv)', 'Every part, colour and quantity'));
  }
  out.push(item('price_estimate', 'tag', 'Price estimate (.md)', 'Rough cost range, line by line', '', { newTab: true }));
  out.push(item('glb', 'cube', '3D model (.glb)', 'For 3D viewers and Blender', 'dark'));
  $('#downloads-grid').innerHTML = out.join('');
  const def = d.variants?.[0]?.title || 'default';
  $('#downloads-intro').textContent = custom
    ? `The shopping lists${vb ? ' and instructions' : ''} match the ${variant.title} colourway. ${vb ? 'The' : 'The instructions and'} LDraw model use${vb ? 's' : ''} the ${def} colours.`
    : 'Instructions, the digital model and ready-made shopping lists.';
  $('#downloads').hidden = false;

  if (f.video && !$('#video-wrap').dataset.done) {
    const poster = bestRender(f.renders);
    $('#video-wrap').innerHTML = `<video controls playsinline preload="metadata" ${poster ? `poster="${media.image(poster, 'lg')}"` : ''}><source src="${media.url(f.video)}" type="video/mp4"></video>`;
    $('#video-wrap').hidden = false;
    $('#video-wrap').dataset.done = '1';
  }
}

// ---------- parts ----------

function swatch(name, hex) {
  const c = state.colourByName.get(name);
  const trans = c && (c.alpha ?? 255) < 255;
  const chrome = c && /chrome|metal|pearl/.test(c.material || '');
  const col = hex || c?.hex || '#999';
  if (trans) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(col.slice(i, i + 2), 16));
    return `<span class="sw trans" style="--c:rgba(${r},${g},${b},0.62)" title="${esc(name)}"></span>`;
  }
  return `<span class="sw${chrome ? ' chrome' : ''}" style="background-color:${esc(col)}" title="${esc(name)}"></span>`;
}

function blLink(r) {
  if (!r.bricklink_part) return '';
  const c = r.bricklink_colour != null && r.bricklink_colour !== '' ? `&C=${encodeURIComponent(r.bricklink_colour)}` : '';
  return `https://www.bricklink.com/v2/catalog/catalogitem.page?P=${encodeURIComponent(r.bricklink_part)}${c}`;
}

const rowKey = (part, colour) => `${part}|${colour}`;

function renderParts() {
  const bom = variantBom();
  if (!bom.length) return;
  $('#parts').hidden = false;
  const q = $('#parts-filter').value.trim().toLowerCase();
  const sort = $('#parts-sort').value;
  let rows = bom.map((r, i) => ({ ...r, i }));
  if (q) rows = rows.filter((r) => [r.name, r.part, r.colour, r.element_id, r.bricklink_part].some((v) => String(v ?? '').toLowerCase().includes(q)));
  const cmpName = (a, b) => String(a.name).localeCompare(String(b.name), 'en', { numeric: true });
  if (sort === 'qty') rows.sort((a, b) => b.qty - a.qty || cmpName(a, b));
  else if (sort === 'name') rows.sort((a, b) => cmpName(a, b) || String(a.colour).localeCompare(b.colour));
  else rows.sort((a, b) => String(a.colour).localeCompare(b.colour) || cmpName(a, b));
  const total = bom.reduce((s, r) => s + r.qty, 0);
  const rare = bom.filter((r) => r.rare).length;
  $('#parts-total').textContent = `${plural(bom.length, 'lot')} · ${plural(total, 'part')}${rare ? ` · ${rare} rare` : ''}`;
  const variant = state.data.variants?.[state.variant];
  $('#parts-intro').textContent = `Every part in the ${variant?.title || 'default'} colourway, with LEGO element IDs and BrickLink links.`;
  $('#parts-body').innerHTML = rows.length ? rows.map((r) => {
    const el = r.element_id ? esc(r.element_id) : '<span class="pid">none</span>';
    const link = blLink(r);
    return `<tr data-key="${esc(rowKey(r.part, r.colour))}" data-name="${esc(rowKey(r.name, r.colour))}">
      <td class="qty">${r.qty}×</td>
      <td><div class="pname">${esc(r.name)}${r.rare ? '<span class="rare" title="Rare: few recent sets use this part in this colour">rare</span>' : ''}</div><div class="pid">${esc(r.part)}</div>
        <div class="sub">${swatch(r.colour, r.hex)}${esc(r.colour)}${r.element_id ? ` · ${esc(r.element_id)}` : ''}</div></td>
      <td class="colour"><span class="colour-inner">${swatch(r.colour, r.hex)}${esc(r.colour)}</span></td>
      <td class="el">${el}</td>
      <td class="link">${link ? `<a class="bl-link" href="${link}" target="_blank" rel="noopener" aria-label="${esc(r.name)} in ${esc(r.colour)} on BrickLink"><span class="bl-text">BrickLink</span>${icon('external')}</a>` : ''}</td>
    </tr>`;
  }).join('') : '<tr class="empty-row"><td colspan="5">No parts match that filter.</td></tr>';
}

function flashRow(part, name, colour) {
  $('#parts-filter').value = '';
  renderParts();
  const row = $(`#parts-body tr[data-key="${CSS.escape(rowKey(part, colour))}"]`) || $(`#parts-body tr[data-name="${CSS.escape(rowKey(name, colour))}"]`);
  if (!row) return;
  const scroller = row.closest('.table-scroll');
  $('#parts').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  setTimeout(() => {
    scroller.scrollTop = row.offsetTop - scroller.clientHeight / 2 + row.offsetHeight / 2;
    row.classList.add('flash');
    setTimeout(() => row.classList.remove('flash'), 1800);
  }, reduceMotion ? 0 : 450);
}

// ---------- price estimate ----------
// Uses a structured `price` {low, high, currency, note} if the export provides one, else the first
// paragraphs of files.price_estimate (markdown written by brickkit).

function mdInline(s) {
  return esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*(.+?)\*/g, '<em>$1</em>');
}

async function renderPrice(d) {
  const f = d.files || {};
  let head = '', note = '', short = '';
  if (d.price && d.price.low != null) {
    const money = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: d.price.currency || 'USD', maximumFractionDigits: 0 }).format(v);
    short = `${money(d.price.low)} – ${money(d.price.high)}`;
    head = `<strong>Roughly ${short}</strong> in new parts, before shipping.`;
    note = esc(d.price.note || 'A rough range from typical per-piece prices, not live market data.');
  } else if (f.price_estimate) {
    try {
      const r = await fetch(state.media.url(f.price_estimate));
      if (!r.ok) return;
      const paras = (await r.text()).split(/\n\s*\n/).map((p) => p.trim().replace(/\s*\n\s*/g, ' ')).filter((p) => p && !/^[#|]/.test(p));
      if (!paras.length) return;
      // drop parentheticals that point at repo files, e.g. "(see `brickkit/data/...`)"
      const clean = (t) => t.replace(/\s*\([^()]*`[^`]*`[^()]*\)/g, '');
      head = mdInline(clean(paras[0]));
      note = paras[1] ? mdInline(clean(paras[1])) : '';
      const m = paras[0].match(/\*\*(?:roughly\s+)?(.+?)\*\*/i);
      short = m ? m[1] : '';
    } catch (e) {
      return;
    }
  }
  if (!head) return;
  const full = f.price_estimate ? `<a href="${state.media.url(f.price_estimate)}" target="_blank" rel="noopener">Full breakdown</a>` : '';
  const def = d.variants?.[0]?.title;
  const card = $('#price-card');
  if (!card) return;
  card.innerHTML = `<span class="pi">${icon('cart')}</span><div><p class="ph">${head}</p>${note ? `<p class="pn">${note}</p>` : ''}${(d.variants || []).length > 1 && def ? `<p class="pn">Estimated for the ${esc(def)} colourway.</p>` : ''}${full ? `<p class="pn">${full}</p>` : ''}</div>`;
  card.hidden = false;
  if (short) {
    const el = $('#price-summary');
    if (!el) return;
    el.innerHTML = `<span class="ring price">${icon('cart')}</span><span><strong>${esc(short)}</strong><span>Estimated parts cost, before shipping</span></span><span class="chev">${icon('chevronRight')}</span>`;
    el.hidden = false;
  }
}

// ---------- gallery ----------

function renderGallery(d) {
  const renders = d.files?.renders || [];
  if (!renders.length) return;
  $('#gallery').hidden = false;
  const media = state.media;
  const cap = (p) => humanize(p.split('/').pop().replace(/\.\w+$/, '').replace(/^renders?_/, '').replace(/^hero_/, 'hero '));
  $('#gallery-grid').innerHTML = renders.map((p) => {
    const info = media.imageInfo(p);
    return `<button class="shot" type="button" data-src="${media.image(p, 'lg')}" data-cap="${esc(cap(p))}" aria-label="Open render: ${esc(cap(p))}">
      <img src="${media.image(p, 'sm')}" alt="${esc(d.name)}: ${esc(cap(p))} render" loading="lazy" decoding="async" width="${info?.w || 800}" height="${info?.h || 800}">
      <span class="cap">${esc(cap(p))}</span></button>`;
  }).join('');
  const dlg = $('#lightbox');
  $$('#gallery-grid .shot').forEach((b) => b.addEventListener('click', () => {
    $('#lightbox-img').src = b.dataset.src;
    $('#lightbox-img').alt = `${d.name}: ${b.dataset.cap}`;
    dlg.showModal();
  }));
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });
}

// ---------- viewer + dock ----------

function stepNodes(d, appear) {
  const by = Array.from({ length: Math.max(1, d.steps?.length || 1) }, () => []);
  appear.forEach((a, i) => by[Math.min(a, by.length - 1)]?.push(i));
  return by;
}

function colourOfNode(i) {
  const d = state.data;
  const code = d.variants?.[state.variant]?.colors?.[i] ?? d.variants?.[0]?.colors?.[i];
  const c = d.colors?.[code] || d.colors?.[String(code)];
  return c ? { name: c.name, hex: c.hex } : { name: 'Unknown', hex: '#999' };
}

function updateBuildUI(i) {
  const d = state.data;
  const steps = d.steps || [];
  if (!steps.length) return;
  state.step = i;
  const range = $('#build-range');
  range.value = String(i);
  range.style.setProperty('--p', `${steps.length > 1 ? (i / (steps.length - 1)) * 100 : 100}%`);
  const s = steps[i];
  const main = steps[steps.length - 1].submodel;
  const isSub = s.submodel && s.submodel !== main;
  const text = s.caption || (isSub ? `Build the ${humanize(s.submodel).toLowerCase()} sub-assembly` : `Step ${i + 1}`);
  const added = state.byStep[i] || [];
  $('#build-caption').innerHTML = `${isSub ? `<span class="tag">${esc(humanize(s.submodel))}</span>` : ''}<span class="txt">${esc(text)}</span>${added.length ? `<span class="added">+${fmtInt(added.length)}</span>` : ''}`;
  if (!$('#panel-build').hidden) $('#dock-meta').innerHTML = `Step <b>${i + 1}</b> / ${steps.length}`;
  $('#step-prev').disabled = i <= 0;
  $('#step-next').disabled = i >= steps.length - 1;
  // parts added in this step, grouped
  const groups = new Map();
  for (const n of added) {
    const node = d.nodes[n];
    const col = colourOfNode(n);
    const k = `${node.name}|${col.name}`;
    const g = groups.get(k) || { name: node.name, col, qty: 0 };
    g.qty++;
    groups.set(k, g);
  }
  const list = [...groups.values()].sort((a, b) => b.qty - a.qty);
  const shown = list.slice(0, 6);
  $('#step-parts').innerHTML = shown.map((g) => `<span class="sp">${swatch(g.col.name, g.col.hex)}${g.qty}× ${esc(g.name)}</span>`).join('') +
    (list.length > shown.length ? `<span class="sp">+${list.length - shown.length} more</span>` : '');
}

function setupDock(d) {
  const steps = d.steps || [];
  const dock = $('#dock');
  dock.hidden = false;
  const range = $('#build-range');
  range.max = String(Math.max(0, steps.length - 1));
  updateBuildUI(steps.length - 1);

  let timer = 0;
  const playBtn = $('#build-play');
  const stop = () => { clearTimeout(timer); timer = 0; playBtn.setAttribute('aria-pressed', 'false'); playBtn.setAttribute('aria-label', 'Play the build'); };
  const go = (i, animate) => { updateBuildUI(i); state.viewer?.setStep(i, { animate }); };
  const tick = () => {
    const next = state.step + 1;
    if (next > steps.length - 1) return stop();
    go(next, true);
    const n = (state.byStep[next] || []).length;
    timer = setTimeout(tick, n ? Math.min(1100, 520 + n * 12) : 380);
  };
  playBtn.addEventListener('click', () => {
    if (timer) return stop();
    playBtn.setAttribute('aria-pressed', 'true');
    playBtn.setAttribute('aria-label', 'Pause the build');
    if (state.step >= steps.length - 1) { go(0, false); timer = setTimeout(tick, 700); } else tick();
  });
  range.addEventListener('input', () => { stop(); go(Number(range.value), false); });
  $('#step-prev').addEventListener('click', () => { stop(); go(Math.max(0, state.step - 1), false); });
  $('#step-next').addEventListener('click', () => { stop(); go(Math.min(steps.length - 1, state.step + 1), true); });
  state.stopBuild = stop;

  // mechanism
  const mech = d.mechanism;
  if (mech) {
    $('#tab-mech').hidden = false;
    const mr = $('#mech-range');
    const mplay = $('#mech-play');
    const moving = d.nodes.filter((n) => n.group).length;
    const [l0, l1] = mech.labels || ['start', 'end'];
    $('#mech-caption').innerHTML = `<span class="txt">${mech.name ? `<b>${esc(mech.name)}</b>: ${esc(l0)} to ${esc(l1)}. ` : ''}${esc(plural(new Set(d.nodes.map((n) => n.group).filter(Boolean)).size, 'moving group'))}, ${esc(plural(moving, 'part'))} in motion. Drag the slider or press play.</span>`;
    let raf = 0, phase = 0, last = 0;
    const setT = (t) => {
      mr.value = String(Math.round(t * 1000));
      mr.style.setProperty('--p', `${t * 100}%`);
      if (!$('#panel-mech').hidden) $('#dock-meta').innerHTML = `<b>${Math.round(t * 100)}</b>% ${esc(l1)}`;
      state.viewer?.setPose(t);
    };
    state.setMechT = setT;
    const mstop = () => { cancelAnimationFrame(raf); raf = 0; mplay.setAttribute('aria-pressed', 'false'); mplay.setAttribute('aria-label', 'Play the mechanism'); };
    const loop = (now) => {
      const dt = last ? (now - last) / 1000 : 0;
      last = now;
      phase = (phase + dt / 5.5) % 1;
      setT((1 - Math.cos(phase * 2 * Math.PI)) / 2);
      raf = requestAnimationFrame(loop);
    };
    mplay.addEventListener('click', () => {
      if (raf) return mstop();
      const t = Number(mr.value) / 1000;
      phase = Math.acos(1 - 2 * t) / (2 * Math.PI);
      last = 0;
      mplay.setAttribute('aria-pressed', 'true');
      mplay.setAttribute('aria-label', 'Pause the mechanism');
      raf = requestAnimationFrame(loop);
    });
    mr.addEventListener('input', () => { mstop(); setT(Number(mr.value) / 1000); });
    state.stopMech = mstop;
    setT(0);
  }

  const tabs = [['#tab-build', '#panel-build'], ['#tab-mech', '#panel-mech']];
  const select = (idx) => {
    tabs.forEach(([t, p], j) => {
      $(t).setAttribute('aria-selected', String(j === idx));
      $(p).hidden = j !== idx;
    });
    if (idx === 1) {
      state.stopBuild?.();
      if (state.step !== steps.length - 1) { updateBuildUI(steps.length - 1); state.viewer?.setStep(steps.length - 1); }
      state.setMechT?.(Number($('#mech-range').value) / 1000);
    } else {
      state.stopMech?.();
      updateBuildUI(state.step);
    }
    state.viewer?.resize();
  };
  $('#tab-build').addEventListener('click', () => select(0));
  $('#tab-mech').addEventListener('click', () => select(1));
  $$('.tabs .tab').forEach((t, i, all) => t.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const vis = all.filter((x) => !x.hidden);
    const j = (vis.indexOf(t) + (e.key === 'ArrowRight' ? 1 : -1) + vis.length) % vis.length;
    vis[j].focus();
    vis[j].click();
  }));
}

function showPartTip(node) {
  const tip = $('#part-tip');
  state.selected = node;
  if (node == null) { tip.hidden = true; return; }
  const d = state.data;
  const n = d.nodes[node];
  const col = colourOfNode(node);
  const appear = state.appear?.[node] ?? n.join;
  tip.innerHTML = `<button class="close" type="button" aria-label="Close">${icon('x')}</button>
    <strong>${esc(n.name)}</strong>
    <div class="row">${swatch(col.name, col.hex)}<span>${esc(col.name)}</span><span class="pid">· ${esc(n.part)}</span></div>
    <div class="row"><span>Added in step ${appear + 1}${n.group ? ` · moves with ${esc(humanize(n.group).toLowerCase())}` : ''}</span></div>
    <div class="row"><a href="#parts" data-find>Find in parts list</a></div>`;
  tip.hidden = false;
  tip.querySelector('.close').addEventListener('click', () => state.viewer?.select(null));
  tip.querySelector('[data-find]').addEventListener('click', (e) => {
    e.preventDefault();
    flashRow(n.part, n.name, col.name);
  });
}

async function initViewer(d) {
  const host = $('#viewer');
  const media = state.media;
  const posterPath = bestRender(d.files?.renders);
  const poster = $('#viewer-poster');
  if (posterPath) { poster.src = media.image(posterPath, 'sm'); poster.hidden = false; }
  const fail = (msg) => {
    host.classList.add('is-fallback');
    if (posterPath) poster.src = media.image(posterPath, 'lg');
    $('#dock').hidden = true;
    $('.viewer-top').hidden = true;
    // No 3D here: play the photoreal turntable loop (the model turning, its mechanism and
    // lights working) if there is one, else keep the still render with a note.
    const tt = d.files?.turntable;
    if (tt && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const v = document.createElement('video');
      for (const a of ['muted', 'loop', 'playsinline', 'autoplay']) v.setAttribute(a, '');
      v.muted = true;
      v.preload = 'auto';
      v.className = 'viewer-turntable';
      v.setAttribute('aria-label', `${d.name}, turning slowly with its moving parts working`);
      if (poster.src) v.poster = poster.src;
      v.src = media.url(tt);
      v.addEventListener('playing', () => host.classList.add('is-turntable'), { once: true });
      poster.after(v);
      v.play?.().catch(() => {});
      $('#viewer-loading').innerHTML = '';
      return;
    }
    $('#viewer-loading').innerHTML = `<div class="loading-card"><p class="viewer-error">${esc(msg)}</p></div>`;
  };
  let mod;
  try {
    mod = await import('./viewer.js');
  } catch (e) {
    console.warn(e);
    return fail('The 3D viewer could not start in this browser. Here is a render instead.');
  }
  if (!mod.hasWebGL2()) return fail('Your browser does not support WebGL 2, so here is a render instead of the 3D view.');
  state.appear = mod.computeAppear(d);
  state.byStep = stepNodes(d, state.appear);
  setupDock(d);

  const bar = $('#loading-bar');
  const dock = $('#dock');
  const viewer = new mod.ModelViewer(host, {
    onProgress: (p) => { bar.style.width = `${Math.round(p * 100)}%`; $('#loading-text').textContent = p < 1 ? `Loading bricks ${Math.round(p * 100)}%` : 'Snapping them together'; },
    onSelect: (n) => showPartTip(n),
    onAutoRotate: (on) => $('#rotate-btn').setAttribute('aria-pressed', String(on)),
    insets: () => ({ top: 60, bottom: dock.hidden ? 0 : dock.offsetHeight + 22 }),
    quality: ({ high: 'high', low: 'low' })[new URLSearchParams(location.search).get('q')] || 'auto',
    onQuality: (q) => { host.dataset.quality = q; },
  });
  state.viewer = viewer;
  host.addEventListener('viewer-error', (e) => fail(e.detail));
  if (state.variant) viewer.variant = state.variant;
  try {
    await viewer.load(media.url(d.files?.glb || 'model.glb'), d);
  } catch (e) {
    console.error(e);
    return fail('The 3D model could not be loaded. Please try again later.');
  }
  host.classList.add('is-ready');
  host.dataset.ready = '1';
  viewer.setStep(state.step);

  // toolbar
  const lightsBtn = $('#lights-btn');
  if (d.lights?.length || d.glow_nodes?.length) {
    lightsBtn.hidden = false;
    lightsBtn.addEventListener('click', () => {
      const on = lightsBtn.getAttribute('aria-pressed') !== 'true';
      lightsBtn.setAttribute('aria-pressed', String(on));
      host.classList.toggle('is-night', on);
      viewer.setLights(on);
    });
  }
  $('#rotate-btn').addEventListener('click', () => viewer.setAutoRotate(!viewer.controls.autoRotate));
  $('#reset-btn').addEventListener('click', () => viewer.resetView());
  const fsBtn = $('#fs-btn');
  if (document.fullscreenEnabled || document.webkitFullscreenEnabled) {
    fsBtn.addEventListener('click', () => {
      const cur = document.fullscreenElement || document.webkitFullscreenElement;
      if (cur) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (host.requestFullscreen || host.webkitRequestFullscreen).call(host);
    });
    const sync = () => {
      const on = !!(document.fullscreenElement || document.webkitFullscreenElement);
      fsBtn.innerHTML = icon(on ? 'shrink' : 'expand');
      fsBtn.setAttribute('aria-label', on ? 'Exit full screen' : 'Full screen');
      setTimeout(() => viewer.resize(), 60);
    };
    document.addEventListener('fullscreenchange', sync);
    document.addEventListener('webkitfullscreenchange', sync);
  } else {
    fsBtn.hidden = true;
  }
  document.addEventListener('themechange', () => viewer.refreshBackground());

  const hint = $('#viewer-hint');
  hint.classList.add('show');
  const hideHint = () => hint.classList.remove('show');
  setTimeout(hideHint, 4500);
  viewer.renderer.domElement.addEventListener('pointerdown', hideHint, { once: true });

  if (!reduceMotion) setTimeout(() => { if (!viewer.userMoved) viewer.setAutoRotate(true); }, 1700);
  window.__viewer = viewer; // handy for debugging and automated checks
}

// ---------- main ----------

async function main() {
  const slug = getSlug();
  if (!slug) return notFound('');
  let text;
  try {
    const r = await fetch(`/models/${encodeURIComponent(slug)}/model.json`, { cache: 'no-cache' });
    if (!r.ok) throw new Error(String(r.status));
    text = await r.text();
  } catch (e) {
    return notFound(slug);
  }
  const d = JSON.parse(text);
  const [mediaJson, conf] = await Promise.all([getJSON('/assets/media.json', { optional: true }), getJSON('/site.json', { optional: true })]);
  state.data = d;
  state.media = new Media(mediaJson, slug, hash(text));
  for (const c of Object.values(d.colors || {})) state.colourByName.set(c.name, c);
  const want = new URLSearchParams(location.search).get('c');
  const vi = (d.variants || []).findIndex((v) => v.name === want);
  if (vi > 0) state.variant = vi;
  if (!document.body.dataset.slug) setMeta(d, slug);
  renderNotices([noticeFor(slug, d, conf)]);

  renderTitle(d);
  renderStats(d);
  renderColourways(d);
  renderFeatures(d);
  renderCheckSummary(d);
  renderCTA(d);
  renderChecks(d);
  renderDownloads();
  renderParts();
  renderGallery(d);
  renderPrice(d);
  $('#parts-filter').addEventListener('input', renderParts);
  $('#parts-sort').addEventListener('change', renderParts);
  await initViewer(d);
}

main().catch((e) => console.error(e));
