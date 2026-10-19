import asyncio

import pytest

from backend.appforge_sandbox import BuildInputError, validate_build_files


def test_build_files_accept_static_project():
    files = validate_build_files({
        "index.html": "<!doctype html><html><body>Hello</body></html>",
        "app.js": "console.log('hello');",
        "styles/app.css": "body { color: #123; }",
    })
    assert len(files) == 3
    assert "index.html" in files


@pytest.mark.parametrize("path", [
    "../secret.txt",
    "/etc/passwd.txt",
    "src/../../secret.js",
    ".env",
    "src/.npmrc",
    "node_modules/package/index.js",
    ".git/config.json",
    "app.exe",
])
def test_build_files_reject_unsafe_paths_and_types(path):
    with pytest.raises(BuildInputError):
        validate_build_files({path: "x", "index.html": "<html></html>"})


def test_build_files_enforces_total_size():
    with pytest.raises(BuildInputError, match="250 KB"):
        validate_build_files({
            "index.html": "<html></html>",
            "app.js": "x" * 251_000,
        })


def test_package_manifest_must_be_valid_json():
    with pytest.raises(BuildInputError, match="valid JSON"):
        validate_build_files({"package.json": "{bad json"})


def test_package_project_may_omit_source_index_until_build_output():
    files = validate_build_files({
        "package.json": '{"scripts":{"build":"node build.js"}}',
        "build.js": "console.log('build')",
    })
    assert "package.json" in files
