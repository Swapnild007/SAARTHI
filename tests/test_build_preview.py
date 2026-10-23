import asyncio
import pytest
from backend.build_preview import self_contained_preview, PreviewUnavailable, asset_path

def test_bundled_css_and_js_are_inlined_from_the_build_output_directory():
    files={'workspace/dist/assets/index.js':'document.querySelector("button").onclick=e=>e.target.textContent="Saved";',
           'workspace/dist/assets/index.css':'body { color: teal; }'}
    async def read(path):return files[path]
    result=asyncio.run(self_contained_preview('<!doctype html><link rel="stylesheet" href="/assets/index.css"><button>Save</button><script type="module" src="/assets/index.js"></script>','workspace/dist/index.html',read))
    assert 'src="/assets' not in result
    assert '<style>body { color: teal; }</style>' in result
    assert '<script type="module">document.querySelector' in result
    assert 'Saved' in result

@pytest.mark.parametrize('reference',['../secret.js','%2e%2e/secret.js','https://other.example/app.js','//other.example/app.js','/a/../secret.js','a\\b.js'])
def test_asset_read_cannot_escape_output_root(reference):
    with pytest.raises(PreviewUnavailable):asset_path('workspace/dist',reference)

@pytest.mark.parametrize('source',["import('./chunk.js')", "import x from './chunk.js'", 'import.meta.url'])
def test_code_split_assets_are_explicitly_unsupported(source):
    async def read(path):return source
    with pytest.raises(PreviewUnavailable,match='hosted preview'):
        asyncio.run(self_contained_preview('<script src="/app.js"></script>','workspace/dist/index.html',read))

def test_missing_build_asset_does_not_produce_a_false_working_preview():
    async def read(path):raise FileNotFoundError()
    with pytest.raises(PreviewUnavailable,match='missing asset'):
        asyncio.run(self_contained_preview('<script src="/app.js"></script>','workspace/dist/index.html',read))

def test_oversized_assets_are_rejected():
    async def read(path):return 'x'*120001
    with pytest.raises(PreviewUnavailable,match='limit'):
        asyncio.run(self_contained_preview('<script src="/app.js"></script>','workspace/dist/index.html',read))
