import json
import shutil
from pathlib import Path

import pytest

from brickkit import paths
from brickkit.project import Project
from brickkit.viewer_export import export_model
from tools.quick_site import build_quick_site, quick_projects


TEMPLATE = '''<!doctype html><html><head><!-- meta:start -->old<!-- meta:end --></head>
<body data-slug=""><h1 data-fill="name"></h1><p data-fill="description"></p></body></html>'''


def add_model(tmp_path, slug, *, video=False, poster=False, pdf=False, quick=True):
    models = tmp_path / 'models'
    project = models / slug
    project.mkdir(parents=True)
    collection = 'quick_bricks' if quick else 'display'
    (project / 'model.toml').write_text(
        f'[model]\nname = "{slug}"\ncollection = "{collection}"\ndescription = "A <tiny> build & friend"\n')
    site = tmp_path / 'site'
    folder = site / 'models' / slug
    folder.mkdir(parents=True)
    files = {'glb': 'model.glb', 'renders': []}
    (folder / 'model.glb').write_bytes(b'geometry')
    if video:
        out = project / 'out'
        out.mkdir()
        (out / f'{slug}-1080x1920.mp4').write_bytes(b'existing video')
    if poster:
        (folder / 'poster.png').write_bytes(b'existing poster')
        files['renders'] = ['poster.png']
    if pdf:
        (folder / 'booklet.pdf').write_bytes(b'%PDF-existing')
        files['booklet'] = 'booklet.pdf'
    (folder / 'model.json').write_text(json.dumps({
        'slug': slug, 'name': f'{slug} & friend', 'collection': collection,
        'parts': 3, 'pieces': 4, 'steps': [{'index': 0}, {'index': 1}], 'files': files,
    }))
    (site / 'quick-model.html').write_text(TEMPLATE)
    return site, models, folder


def test_quick_index_includes_every_configured_model_without_video(tmp_path):
    site, models, _ = add_model(tmp_path, 'zebra', video=True, poster=True, pdf=True)
    add_model(tmp_path, 'apple', poster=True)
    add_model(tmp_path, 'regular', quick=False)
    result = build_quick_site(site, models)
    assert [r['slug'] for r in result['models']] == ['apple', 'zebra']
    apple, zebra = result['models']
    assert apple['video'] is None and apple['instructions'] is None
    assert apple['poster'].startswith('/models/apple/poster.png?v=')
    assert zebra['video'].startswith('/quick/zebra-1080x1920.mp4?v=')
    assert zebra['instructions'].startswith('/models/zebra/booklet.pdf?v=')
    assert zebra['pieces'] == 4 and zebra['steps'] == 2
    assert all(r['collection'] == 'quick_bricks' for r in result['models'])
    assert all(r['model'].startswith(f"/models/{r['slug']}/model.json?v=") for r in result['models'])
    assert all(r['geometry'].startswith(f"/models/{r['slug']}/model.glb?v=") for r in result['models'])
    assert json.loads((site / 'quick/models.json').read_text()) == result
    assert not (site / 'm').exists()
    page = (site / 'quick/apple/index.html').read_text()
    assert 'data-slug="apple"' in page and 'apple &amp; friend' in page
    assert 'A &lt;tiny&gt; build &amp; friend' in page
    assert 'https://bricks.superfun.games/quick/apple/' in page
    assert '/m/apple/' not in page
    # Deterministic reruns do not rewrite JSON/pages or change existing media.
    stamp = (site / 'quick/models.json').stat().st_mtime_ns
    assert build_quick_site(site, models) == result
    assert (site / 'quick/models.json').stat().st_mtime_ns == stamp


def test_geometry_url_changes_without_a_model_json_change(tmp_path):
    site, models, folder = add_model(tmp_path, 'cake')
    before = build_quick_site(site, models)['models'][0]
    metadata = (folder / 'model.json').read_bytes()
    (folder / 'model.glb').write_bytes(b'geometry with a changed part transform')
    after = build_quick_site(site, models)['models'][0]
    assert (folder / 'model.json').read_bytes() == metadata
    assert after['model'] == before['model']
    assert after['geometry'] != before['geometry']
    assert after['geometry'].startswith('/models/cake/model.glb?v=')


def test_existing_published_video_is_retained_when_local_video_is_archived(tmp_path):
    site, models, _ = add_model(tmp_path, 'bat')
    (site / 'quick').mkdir()
    video = site / 'quick/bat-1080x1920.mp4'
    video.write_bytes(b'published')
    item = build_quick_site(site, models)['models'][0]
    assert item['video'].startswith('/quick/bat-1080x1920.mp4?v=')
    assert video.read_bytes() == b'published'
    assert item['poster'] is None and item['instructions'] is None


def test_missing_or_stale_quick_export_cannot_silently_drop_a_model(tmp_path):
    site, models, folder = add_model(tmp_path, 'cake')
    path = folder / 'model.json'
    data = json.loads(path.read_text())
    data.pop('collection')
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='stale'):
        build_quick_site(site, models)
    path.unlink()
    with pytest.raises(FileNotFoundError, match='cake'):
        build_quick_site(site, models)


def test_removed_models_only_remove_generated_pages_and_preserve_media(tmp_path):
    site, models, _ = add_model(tmp_path, 'bird', video=True)
    build_quick_site(site, models)
    custom = site / 'quick/custom/index.html'
    custom.parent.mkdir()
    custom.write_text('handwritten')
    shutil.rmtree(models / 'bird')
    assert build_quick_site(site, models)['models'] == []
    assert not (site / 'quick/bird/index.html').exists()
    assert (site / 'quick/bird-1080x1920.mp4').read_bytes() == b'existing video'
    assert custom.read_text() == 'handwritten'


def test_collection_survives_viewer_export_and_global_index(engine, tmp_path):
    models = tmp_path / 'models'
    shutil.copytree(paths.MODELS_DIR / '_sample', models / 'quick_sample',
                    ignore=shutil.ignore_patterns('out', '__pycache__'))
    project = Project('quick_sample', models)
    project.config['model']['collection'] = 'quick_bricks'
    (project.out / 'quick_poster.jpg').write_bytes(b'existing poster')
    site = tmp_path / 'site'
    directory = export_model(engine, project, project.build(engine.catalog), site)
    data = json.loads((directory / 'model.json').read_text())
    assert data['collection'] == 'quick_bricks'
    assert (directory / data['files']['quick_poster']).read_bytes() == b'existing poster'
    item = json.loads((site / 'models.json').read_text())['models'][0]
    assert item['collection'] == 'quick_bricks' and item['steps'] == len(data['steps'])


def test_site_assets_routes_quick_pages_separately_and_keeps_regular_pages(tmp_path, monkeypatch):
    from tools import site_assets
    site, models, _ = add_model(tmp_path, 'quickie', poster=True)
    add_model(tmp_path, 'display', quick=False)
    (site / 'models.json').write_text(json.dumps({'models': [
        {'slug': 'quickie', 'collection': 'quick_bricks'}, {'slug': 'display'}]}))
    (site / 'index.html').write_text('<!doctype html><title>Home</title>')
    (site / 'model.html').write_text(TEMPLATE)
    (site / 'quick').mkdir()
    (site / 'quick/index.html').write_text('<!doctype html><title>QuickBricks</title>')
    stale = site / 'm/quickie/index.html'
    stale.parent.mkdir(parents=True)
    stale.write_text(site_assets.GENERATED + 'stale regular page')
    monkeypatch.setattr(site_assets, 'ROOT', tmp_path)
    monkeypatch.setattr(site_assets, 'SITE', site)
    for name in ('build_brand', 'build_manifest', 'og_home'):
        monkeypatch.setattr(site_assets, name, lambda: None)
    monkeypatch.setattr(site_assets, 'model_media', lambda *a: {'images': {}, 'files': {}})
    def og(model, *_):
        path = site / 'assets/og' / f"{model['slug']}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'existing og')
        return path
    monkeypatch.setattr(site_assets, 'og_model', og)
    assert site_assets.main() == 0
    assert (site / 'm/display/index.html').is_file()
    assert not (site / 'm/quickie/index.html').exists()
    assert (site / 'quick/quickie/index.html').is_file()
    sitemap = (site / 'sitemap.xml').read_text()
    assert '/quick/quickie/' in sitemap and '/quick/</loc>' in sitemap
    assert '/m/display/' in sitemap and '/m/quickie/' not in sitemap
