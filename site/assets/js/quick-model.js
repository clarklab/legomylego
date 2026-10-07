// A compact instruction page for Quick Bricks. Uses existing exports and media only.
import { initSite, $, $$, esc, fmtInt, getJSON, humanize } from './site.js';
import { icon } from './icons.js';

initSite();

const state = { data: null, entry: null, viewer: null, step: 0, complete: false, byStep: null, modelURL: null, bookletURL: null };
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function slugFromPage() {
  if (document.body.dataset.slug) return document.body.dataset.slug;
  const query = new URLSearchParams(location.search).get('m');
  if (query) return query;
  try { return decodeURIComponent(location.pathname.match(/^\/quick\/([^/]+)\/?$/)?.[1] || ''); }
  catch { return ''; }
}

function webURL(value, base = location.href) {
  if (!value) return null;
  try {
    const url = new URL(value, base);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function modelAsset(path) {
  const href = webURL(path, state.modelURL || location.href);
  if (!href) return null;
  const url = new URL(href);
  const version = new URL(state.modelURL).searchParams.get('v');
  if (version && !url.searchParams.has('v')) url.searchParams.set('v', version);
  return url.href;
}

function failPage(message, notFound = false) {
  $('#qd-content').hidden = true;
  const error = $('#qd-error');
  error.hidden = false;
  error.innerHTML = `<h2>${notFound ? 'Build not found' : 'The bricks are taking a little longer'}</h2><p>${esc(message)}</p><a class="btn" href="/quick/">Explore Quick Bricks ${icon('arrowRight')}</a>`;
  document.title = `${notFound ? 'Build not found' : 'Quick Bricks'} | Bricks`;
  $('[data-fill="description"]').textContent = '';
}

function renderEntry(entry) {
  $$('[data-fill="name"]').forEach((element) => { element.textContent = entry.name; });
  $$('[data-fill="description"]').forEach((element) => { element.textContent = entry.description || ''; });
  document.title = `${entry.name} instructions | Quick Bricks`;
  $('#qd-stats').innerHTML = `<p>${icon('brick')}<strong>${fmtInt(entry.pieces)}</strong> pieces</p><p>${icon('steps')}<strong>${fmtInt(entry.steps)}</strong> steps</p>`;
  const poster = webURL(entry.poster);
  if (poster) {
    const image = $('#qd-poster');
    image.src = poster;
    image.alt = `${entry.name}, the completed model`;
    image.hidden = false;
    image.addEventListener('error', () => {
      image.hidden = true;
      if (!state.viewer && $('#qd-viewer').getAttribute('aria-busy') === 'false') {
        $('#qd-loading').hidden = false;
        $('#qd-loading-text').textContent = 'Follow the instructions alongside this view.';
      }
    }, { once: true });
  }
  const video = webURL(entry.video);
  if (video) {
    const details = $('#qd-video-details');
    const player = $('#qd-video');
    details.hidden = false;
    player.setAttribute('aria-label', `${entry.name} build video`);
    if (poster) player.poster = poster;
    details.addEventListener('toggle', () => {
      if (details.open && !player.getAttribute('src')) player.src = video;
      if (!details.open) player.pause();
    });
    player.addEventListener('error', () => { $('#qd-video-error').hidden = false; });
  }
  renderDownloads();
}

function renderDownloads() {
  const files = state.data?.files || {};
  const pdf = webURL(state.entry.instructions) || (files.booklet ? modelAsset(files.booklet) : null);
  const links = [];
  const add = (url, name, symbol, pdfLink = false) => {
    if (url) links.push(`<a class="qd-download-link" href="${esc(url)}"${pdfLink ? ' target="_blank" rel="noopener"' : ' download'}>${icon(symbol)}${esc(name)}</a>`);
  };
  add(pdf, 'Instructions PDF', 'book', true);
  add(files.parts_csv ? modelAsset(files.parts_csv) : null, 'Parts list · CSV', 'list');
  add(files.mpd ? modelAsset(files.mpd) : null, 'Digital model · MPD', 'cube');
  $('#qd-download-links').innerHTML = links.join('');
  $('#qd-pdf-note').hidden = !!pdf;
  renderBooklet(pdf);
  renderShopping(files);
}

function renderBooklet(pdf) {
  $('#instruction-booklet').hidden = !pdf;
  $('#qd-booklet-jump').hidden = !pdf;
  if (!pdf || state.bookletURL === pdf) return;
  state.bookletURL = pdf;
  $('#qd-booklet-open').href = pdf;
  $('#qd-booklet-frame').title = `${state.entry.name} building instructions`;
  $('#qd-booklet-frame').src = `${pdf}#view=FitH`;
}

function renderShopping(files) {
  const shops = [
    { file: files.pick_a_brick_csv, name: 'LEGO Pick a Brick', label: 'Download Pick a Brick list', format: 'CSV',
      url: 'https://www.lego.com/en-us/pick-and-build/pick-a-brick', action: 'Open Pick a Brick',
      description: 'Download the list of LEGO element IDs and quantities, then upload it to Pick a Brick.' },
    { file: files.bricklink_xml, name: 'BrickLink', label: 'Download BrickLink wanted list', format: 'XML',
      url: 'https://www.bricklink.com/v2/wanted/upload.page', action: 'Upload to BrickLink',
      description: 'Copy the downloaded XML into BrickLink’s “Upload BrickLink XML format” tab.' },
  ].filter(shop => shop.file);
  $('#get-pieces').hidden = !shops.length;
  $('#qd-shopping-links').innerHTML = shops.map(shop => `<article class="qd-shop">
    <h3>${esc(shop.name)}</h3><p>${esc(shop.description)}</p>
    <a class="qd-shop-download" href="${esc(modelAsset(shop.file))}" download>${icon('download')}<span>${esc(shop.label)} <span class="qd-file-type">${shop.format}</span></span></a>
    <a class="qd-shop-visit" href="${shop.url}" target="_blank" rel="noopener">${esc(shop.action)}${icon('external')}</a>
  </article>`).join('');
}

function colorFor(index) {
  const code = state.data.variants?.[0]?.colors?.[index];
  return state.data.colors?.[code] || { name: 'Colour not listed', hex: '#999999' };
}

function pieceMarkup({ name, color, quantity, part }) {
  const hex = /^#[\da-f]{3,8}$/i.test(color.hex || '') ? color.hex : '#999999';
  return `<li class="qd-piece"><i class="qd-piece-color" style="--piece-color:${hex}" aria-hidden="true"></i><p class="qd-piece-quantity">${fmtInt(quantity)}×</p><div class="qd-piece-label"><p>${esc(name || part || 'Piece')}</p><p>${esc(color.name)}${part ? ` · ${esc(part)}` : ''}</p></div></li>`;
}

function renderInventory() {
  const bom = state.data.variants?.[0]?.bom || [];
  if (!bom.length) return;
  $('#qd-inventory').hidden = false;
  $('#qd-inventory-total').textContent = `${fmtInt(bom.reduce((sum, part) => sum + part.qty, 0))} pieces`;
  $('#qd-inventory-list').innerHTML = bom.map((part) => pieceMarkup({ name: part.name, part: part.part, quantity: part.qty, color: { name: part.colour, hex: part.hex } })).join('');
}

function renderStepParts() {
  const container = $('#qd-step-parts');
  if (state.complete || !state.byStep) { container.hidden = true; return; }
  const nodes = state.byStep[state.step] || [];
  const groups = new Map();
  nodes.forEach((index) => {
    const node = state.data.nodes[index];
    const color = colorFor(index);
    const key = `${node.part}|${color.name}`;
    const item = groups.get(key) || { name: node.name, part: node.part, color, quantity: 0 };
    item.quantity++;
    groups.set(key, item);
  });
  container.hidden = !groups.size;
  $('#qd-parts-title').textContent = `Add ${fmtInt(nodes.length)} ${nodes.length === 1 ? 'piece' : 'pieces'}`;
  $('#qd-parts-list').innerHTML = [...groups.values()].map(pieceMarkup).join('');
}

function showStep(index, complete = false) {
  const steps = state.data.steps || [];
  if (!steps.length) return;
  state.complete = complete;
  state.step = Math.max(0, Math.min(steps.length - 1, index));
  const step = steps[state.step];
  const subassembly = step.submodel !== steps.at(-1).submodel;
  $('#qd-step-label').textContent = complete ? 'Ready when you are' : `Step ${state.step + 1} of ${steps.length}`;
  $('#qd-caption').textContent = complete ? 'One brick at a time.' : (step.caption || (subassembly ? `Build the ${humanize(step.submodel).toLowerCase()}` : `Build step ${state.step + 1}`)).replace(/^\d+\s*[.·]\s*/, '');
  $('#qd-step-description').textContent = complete ? 'Turn the model around, then follow the steps at your own pace.' : subassembly ? 'Build this small section before adding it to the model.' : state.step === steps.length - 1 ? 'The last pieces are in. Your little build is complete.' : 'Use the view to see where each piece fits. You can turn it around at any step.';
  $('#qd-start').hidden = !complete;
  $('#qd-complete').hidden = complete;
  $('#qd-step-controls').hidden = complete;
  $('#qd-step-select').value = String(state.step);
  $('#qd-prev').disabled = state.step === 0;
  $('#qd-next').disabled = state.step === steps.length - 1;
  $('#qd-progress-fill').style.setProperty('--qd-progress', `${((state.step + 1) / steps.length) * 100}%`);
  $('#qd-part-tip').hidden = true;
  renderStepParts();
  state.viewer?.setStep(state.step, { animate: !complete && !reducedMotion });
}

function setupSteps() {
  const steps = state.data.steps || [];
  if (!steps.length) {
    $('#qd-start').hidden = true;
    $('#qd-caption').textContent = 'Explore the finished build.';
    $('#qd-step-description').textContent = 'Building steps are not available for this model. Find the available files below.';
    return;
  }
  $('#qd-stats').innerHTML = `<p>${icon('brick')}<strong>${fmtInt(state.data.pieces ?? state.data.parts)}</strong> pieces</p><p>${icon('steps')}<strong>${steps.length}</strong> steps</p>`;
  $('#qd-step-select').innerHTML = steps.map((step, index) => `<option value="${index}">${index + 1} / ${steps.length}</option>`).join('');
  $('#qd-start').disabled = false;
  $('#qd-start').addEventListener('click', () => { showStep(0); $('#qd-step-select').focus({ preventScroll: true }); });
  $('#qd-complete').addEventListener('click', () => { showStep(steps.length - 1, true); $('#qd-start').focus({ preventScroll: true }); });
  $('#qd-prev').addEventListener('click', () => showStep(state.step - 1));
  $('#qd-next').addEventListener('click', () => showStep(state.step + 1));
  $('#qd-step-select').addEventListener('change', (event) => showStep(Number(event.target.value)));
  $('#qd-caption').setAttribute('aria-live', 'polite');
  showStep(0);
}

function viewerFallback(message) {
  state.viewer = null;
  $('#qd-viewer').setAttribute('aria-busy', 'false');
  $('#qd-viewer-tools').hidden = true;
  $('#qd-drag-hint').hidden = true;
  $('#qd-viewer').querySelectorAll('canvas').forEach((canvas) => { canvas.hidden = true; });
  $('#qd-loading').hidden = true;
  const poster = $('#qd-poster');
  if (poster.getAttribute('src') && !(poster.complete && !poster.naturalWidth)) poster.hidden = false;
  else {
    $('#qd-loading').hidden = false;
    $('#qd-loading-text').textContent = 'Follow the instructions alongside this view.';
  }
  $('#qd-viewer-note').textContent = message;
  $('#qd-viewer-note').hidden = false;
}

async function loadViewer() {
  let mod;
  try { mod = await import('./viewer.js'); }
  catch { viewerFallback('The 3D viewer could not load. The written steps and downloads are still available.'); return; }
  state.byStep = Array.from({ length: state.data.steps.length }, () => []);
  mod.computeAppear(state.data).forEach((step, index) => state.byStep[step]?.push(index));
  renderStepParts();
  if (!mod.hasWebGL2()) { viewerFallback('This browser cannot display the 3D model. Follow the written steps or open the instructions PDF, when available.'); return; }
  const host = $('#qd-viewer');
  host.addEventListener('viewer-error', () => viewerFallback('The 3D view was interrupted. Reload the page to try again; your instructions remain available.'));
  try {
    const viewer = new mod.ModelViewer(host, {
      quality: 'auto',
      insets: () => ({ top: 48, bottom: 44 }),
      onProgress: (progress) => { $('#qd-loading-text').textContent = `Getting the bricks ready… ${Math.round(progress * 100)}%`; },
      onSelect: (index) => {
        const note = $('#qd-part-tip');
        if (index == null || !state.data.nodes[index]) { note.hidden = true; return; }
        const node = state.data.nodes[index];
        note.textContent = `${node.name || node.part} · ${colorFor(index).name}`;
        note.hidden = false;
      },
    });
    state.viewer = viewer;
    await viewer.load(webURL(state.entry.geometry) || modelAsset(state.data.files.glb), state.data);
    // A context-loss event may have switched to fallback while the file loaded.
    if (state.viewer !== viewer) return;
    viewer.setStep(state.step);
    host.dataset.ready = '1';
    host.setAttribute('aria-busy', 'false');
    $('#qd-poster').hidden = true;
    $('#qd-loading').hidden = true;
    $('#qd-viewer-tools').hidden = false;
    $('#qd-drag-hint').hidden = false;
    $('#qd-reset').addEventListener('click', () => viewer.resetView());
    document.addEventListener('themechange', () => viewer.refreshBackground());
  } catch { viewerFallback('The 3D model could not load. You can still use the steps, pieces and downloads.'); }
}

async function main() {
  const slug = slugFromPage();
  if (!slug) { failPage('Choose a little model from the Quick Bricks collection.', true); return; }
  let collection;
  try { collection = await getJSON('/quick/models.json'); }
  catch { failPage('We could not load the collection. Please reload the page or try again shortly.'); return; }
  const entry = collection.models?.find((model) => model.slug === slug);
  if (!entry) { failPage('This model is not in the Quick Bricks collection. Find your next build below.', true); return; }
  state.entry = entry;
  state.modelURL = webURL(entry.model);
  renderEntry(entry);
  if (!state.modelURL) { viewerFallback('Instructions are not available for this model yet.'); $('#qd-start').hidden = true; return; }
  try { state.data = await getJSON(state.modelURL); }
  catch {
    viewerFallback('The model instructions could not load. Please reload to try again.');
    $('#qd-start').hidden = true;
    $('#qd-caption').textContent = 'The instructions could not load.';
    $('#qd-step-description').textContent = 'You can still open any available instructions PDF or watch the build below.';
    return;
  }
  state.data.steps ||= [];
  state.data.nodes ||= [];
  renderDownloads();
  renderInventory();
  setupSteps();
  if (state.data.files?.glb) await loadViewer();
  else viewerFallback('A 3D view is not available. Follow the written steps and piece list alongside it.');
}

main().catch(() => failPage('Something interrupted the instructions. Please reload the page to try again.'));
