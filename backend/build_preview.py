"""Make bounded, self-contained previews from isolated static build output.

Read only assets referenced by the chosen HTML entry, under that output root.
Code-split apps and runtime servers require a separate managed preview host.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

LIMIT = 120_000

class PreviewUnavailable(ValueError):
    pass

def asset_path(root: str, reference: str) -> str:
    url = urlsplit(reference)
    path = unquote(url.path)
    if url.scheme or url.netloc or not path or "\\" in path or "\x00" in path:
        raise PreviewUnavailable("External or malformed build asset reference")
    relative = path.lstrip("/")
    if any(part in {"..", ".", ""} for part in relative.split("/")):
        raise PreviewUnavailable("Unsafe build asset reference")
    return str(PurePosixPath(root) / relative)

class _Entry(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.assets: list[tuple[str, str, str]] = []
        self.suppress_script = False
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "base":
            raise PreviewUnavailable("Custom base URLs require hosted previews")
        if tag == "script" and values.get("src"):
            ref = values["src"]
            token = f"__SAARTHI_BUILD_ASSET_{len(self.assets)}__"
            self.assets.append((token, "script", ref))
            attributes = "".join(f' {html.escape(k, quote=True)}="{html.escape(v or "", quote=True)}"' for k,v in attrs if k not in {"src","crossorigin","integrity","defer","async"})
            self.output.append(f"<script{attributes}>{token}</script>")
            self.suppress_script = True
        elif tag == "link" and values.get("rel", "").lower() == "stylesheet":
            token = f"__SAARTHI_BUILD_ASSET_{len(self.assets)}__"
            self.assets.append((token, "style", values.get("href", "")))
            self.output.append(f"<style>{token}</style>")
        elif tag == "link" and values.get("rel", "").lower() in {"modulepreload", "preload"}:
            pass
        else:
            for name in ("src", "srcset", "poster"):
                if values.get(name) and not values[name].startswith("data:"):
                    raise PreviewUnavailable("Media assets require a hosted preview")
            self.output.append(self.get_starttag_text())
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
    def handle_endtag(self, tag):
        if tag == "script" and self.suppress_script:
            self.suppress_script = False
        else:
            self.output.append(f"</{tag}>")
    def handle_data(self, data):
        if not self.suppress_script:
            self.output.append(data)
    def handle_decl(self, decl): self.output.append(f"<!{decl}>")
    def handle_comment(self, data): self.output.append(f"<!--{data}-->")
    def handle_entityref(self, name): self.output.append(f"&{name};")
    def handle_charref(self, name): self.output.append(f"&#{name};")

async def self_contained_preview(entry: str, entry_path: str, read_text) -> str:
    if len(entry.encode()) > LIMIT:
        raise PreviewUnavailable("Build preview exceeds the supported limit")
    parser = _Entry()
    parser.feed(entry)
    if len(parser.assets) > 20:
        raise PreviewUnavailable("Too many build assets for an inline preview")
    root = str(PurePosixPath(entry_path).parent)
    result = "".join(parser.output)
    for token, kind, reference in parser.assets:
        path = asset_path(root, reference)
        if not path.endswith((".js", ".mjs") if kind == "script" else (".css",)):
            raise PreviewUnavailable("Unsupported build asset type")
        try:
            content = await read_text(path)
        except Exception:
            raise PreviewUnavailable("Build output references a missing asset") from None
        if not isinstance(content, str) or len(content.encode()) > LIMIT:
            raise PreviewUnavailable("Build asset exceeds the supported limit")
        if kind == "script":
            if re.search(r"\bimport\s*(?:\(|['\"{*]|[\w$]+\s*(?:,|from))|\b(?:export\s+.*?\s+from|import\.meta)\b", content):
                raise PreviewUnavailable("Code-split modules require a hosted preview")
            content = re.sub(r"</script", r"<\\/script", content, flags=re.I)
        else:
            if re.search(r"@import\b|url\(\s*['\"]?(?!data:)", content, re.I):
                raise PreviewUnavailable("External CSS assets require a hosted preview")
            content = re.sub(r"</style", r"<\\/style", content, flags=re.I)
        result = result.replace(token, content, 1)
        if len(result.encode()) > LIMIT:
            raise PreviewUnavailable("Combined preview exceeds the supported limit")
    return result
