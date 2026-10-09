"""Targeted, page-preserving draw.io file operations. No remote image fetching."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

PAGE_LIMIT = 64 * 1024 * 1024
IMAGE = re.compile(r"image=(?P<uri>data:image/(?P<kind>[^;,]+)(?:;base64)?,(?P<body>[^;]*))")


def parse_xml(data: bytes) -> ET.Element:
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD and ENTITY declarations are not accepted")
    return ET.fromstring(data)


def decode_page(page: ET.Element) -> ET.Element:
    model = page.find("mxGraphModel")
    if model is not None:
        return model
    text = (page.text or "").strip()
    if not text:
        raise ValueError(f"Empty diagram: {page.get('id')}")
    raw = base64.b64decode(text, validate=True)
    decoder = zlib.decompressobj(-15)
    inflated = decoder.decompress(raw, PAGE_LIMIT + 1)
    if len(inflated) > PAGE_LIMIT or decoder.unconsumed_tail:
        raise ValueError("Decoded diagram exceeds size limit")
    inflated += decoder.flush(PAGE_LIMIT + 1 - len(inflated))
    if len(inflated) > PAGE_LIMIT or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid or oversized compressed diagram")
    model = parse_xml(urllib.parse.unquote_to_bytes(inflated.decode("utf-8")))
    if model.tag != "mxGraphModel":
        raise ValueError("Decoded page is not mxGraphModel")
    return model


class Document:
    def __init__(self, source: Path, max_file_mib: int = 256):
        self.source = Path(source).resolve()
        if self.source.stat().st_size > max_file_mib * 1024 * 1024:
            raise ValueError("Input exceeds configured file-size limit")
        self.root = parse_xml(self.source.read_bytes())
        if self.root.tag == "mxGraphModel":
            model = self.root
            self.root = ET.Element("mxfile")
            page = ET.SubElement(self.root, "diagram", {"id": "page-1", "name": "Page-1"})
            page.append(model)
        if self.root.tag != "mxfile":
            raise ValueError("Input is not native draw.io XML")
        self.pages = self.root.findall("diagram")
        if not self.pages:
            raise ValueError("Document contains no pages")
        self.models = [decode_page(p) for p in self.pages]

    def page_index(self, page_id: str) -> int:
        hits = [i for i, p in enumerate(self.pages) if p.get("id") == page_id]
        if len(hits) != 1:
            raise ValueError("Target page id must match exactly one page")
        return hits[0]

    def install_model(self, index: int, model: ET.Element):
        page = self.pages[index]
        for child in list(page):
            page.remove(child)
        page.text = None
        page.append(model)
        self.models[index] = model

    def signature(self, ignore_images: bool = False) -> str:
        normalized = copy.deepcopy(self.root)
        for page, model in zip(normalized.findall("diagram"), self.models):
            for child in list(page):
                page.remove(child)
            page.text = None
            model = copy.deepcopy(model)
            if ignore_images:
                for cell in model.iter("mxCell"):
                    if "style" in cell.attrib:
                        cell.set("style", IMAGE.sub("image=EMBEDDED_IMAGE", cell.get("style", "")))
            page.append(model)
        return hashlib.sha256(ET.tostring(normalized, encoding="utf-8")).hexdigest()

    def write(self, destination: Path):
        destination = Path(destination).resolve()
        if destination == self.source:
            raise ValueError("Output must differ from the original")
        if destination.suffix.lower() != ".drawio":
            raise ValueError("Editable output must end in .drawio")
        payload = ET.tostring(self.root, encoding="utf-8", xml_declaration=True)
        parse_xml(payload)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(payload)
        return destination


def cells(model):
    parents = {child: parent for parent in model.iter() for child in parent}
    for cell in model.iter("mxCell"):
        parent = parents.get(cell)
        owner = parent if parent is not None and parent.tag in ("object", "UserObject") else cell
        yield cell, owner, cell.get("id") or owner.get("id")


def inventory(doc: Document):
    result = {"source": str(doc.source), "bytes": doc.source.stat().st_size, "pages": [], "errors": []}
    page_ids = [p.get("id") for p in doc.pages]
    if len(set(page_ids)) != len(page_ids):
        result["errors"].append("Duplicate page ids")
    for page, model in zip(doc.pages, doc.models):
        entries = list(cells(model))
        ids = [identifier for _, _, identifier in entries]
        id_set = set(ids)
        errors = []
        if None in ids:
            errors.append("Cell without id")
        seen = set()
        for identifier in ids:
            if identifier in seen:
                errors.append(f"Duplicate cell id: {identifier}")
            seen.add(identifier)
        images, external = [], []
        for cell, owner, identifier in entries:
            for key in ("parent", "source", "target"):
                if cell.get(key) is not None and cell.get(key) not in id_set:
                    errors.append(f"Missing {key} {cell.get(key)} for {identifier}")
            style = cell.get("style", "")
            match = IMAGE.search(style)
            if match:
                try:
                    payload = base64.b64decode(urllib.parse.unquote(match["body"]), validate=True)
                    images.append({"id": identifier, "mime": match["kind"], "bytes": len(payload)})
                except Exception:
                    images.append({"id": identifier, "mime": match["kind"], "invalid_base64": True})
                    # SVG data may be URL-encoded text rather than base64.
                    if match["kind"].lower() != "svg+xml":
                        errors.append(f"Invalid embedded image payload for {identifier}")
            elif "image=" in style:
                external.append({"id": identifier, "kind": "external-or-other-image-reference"})
        vertices = [(c, o, i) for c, o, i in entries if c.get("vertex") == "1"]
        edges = [(c, o, i) for c, o, i in entries if c.get("edge") == "1"]
        independent_text = sum(1 for c, _, _ in vertices if re.search(r"(?:^|;)text(?:;|$)", c.get("style", "")))
        result["pages"].append({"id": page.get("id"), "name": page.get("name"), "vertices": len(vertices),
            "edges": len(edges), "bound_edges": sum(1 for c, _, _ in edges if c.get("source") and c.get("target")),
            "independent_text": independent_text, "images": images, "external_images": external, "errors": errors})
        result["errors"].extend(f"{page.get('id')}: {e}" for e in errors)
    result["valid"] = not result["errors"]
    return result


def require_valid(doc):
    data = inventory(doc)
    if not data["valid"]:
        raise ValueError("Structural errors: " + "; ".join(data["errors"]))
    return data


def compress(doc, destination, quality=90, max_side=0, flatten_alpha=False, background="#FFFFFF", force_jpeg=False):
    from PIL import Image, ImageColor, ImageOps
    if not 1 <= quality <= 100 or max_side < 0:
        raise ValueError("Invalid image quality or max-side")
    before = doc.signature(ignore_images=True)
    require_valid(doc)
    records = []
    for page_index, model in enumerate(doc.models):
        changed = False
        for cell, _, identifier in cells(model):
            style = cell.get("style", "")
            match = IMAGE.search(style)
            if not match:
                continue
            uri_normalized = ";base64," in match["uri"]
            if uri_normalized:
                # mxGraph styles use semicolons as separators. Native draw.io embeds
                # base64 images without the standard data-URI ;base64 token.
                canonical = "image=" + match["uri"].replace(";base64,", ",", 1)
                style = style[:match.start()] + canonical + style[match.end():]
                cell.set("style", style)
                match = IMAGE.search(style)
                changed = True
            record = {"page_id": doc.pages[page_index].get("id"), "id": identifier, "source_type": match["kind"],
                "uri_normalized": uri_normalized}
            if match["kind"].lower() not in ("png", "jpeg", "jpg", "webp", "gif"):
                records.append({**record, "action": "kept", "reason": "vector-or-unsupported-format"})
                continue
            original = base64.b64decode(urllib.parse.unquote(match["body"]), validate=True)
            with Image.open(io.BytesIO(original)) as image:
                image.load()
                if getattr(image, "n_frames", 1) > 1:
                    records.append({**record, "action": "kept", "reason": "animated-image"})
                    continue
                original_size = image.size
                image = ImageOps.exif_transpose(image)
                if max_side and max(image.size) > max_side:
                    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                has_alpha = "A" in image.getbands() or "transparency" in image.info
                if has_alpha and not flatten_alpha:
                    rendered = image.convert("RGBA")
                    fmt, mime, save_args = "PNG", "png", {"optimize": True}
                else:
                    if has_alpha:
                        rgba = image.convert("RGBA")
                        rendered = Image.new("RGB", rgba.size, ImageColor.getrgb(background))
                        rendered.paste(rgba, mask=rgba.getchannel("A"))
                    else:
                        rendered = image.convert("RGB")
                    fmt, mime, save_args = "JPEG", "jpeg", {"quality": quality, "optimize": True, "subsampling": 0}
                buffer = io.BytesIO()
                rendered.save(buffer, format=fmt, **save_args)
                encoded = buffer.getvalue()
                with Image.open(io.BytesIO(encoded)) as check:
                    check.load()
                    if check.size != rendered.size or check.format != fmt:
                        raise ValueError("Image re-encoding verification failed")
                if len(encoded) >= len(original) and not (force_jpeg and fmt == "JPEG") and rendered.size == original_size:
                    records.append({**record, "action": "kept", "reason": "new-encoding-not-smaller",
                        "before_bytes": len(original), "candidate_bytes": len(encoded)})
                    continue
                replacement = f"image=data:image/{mime}," + base64.b64encode(encoded).decode("ascii")
                cell.set("style", style[:match.start()] + replacement + style[match.end():])
                changed = True
                records.append({**record, "action": "converted", "new_type": mime,
                    "before_bytes": len(original), "after_bytes": len(encoded),
                    "original_pixels": original_size, "new_pixels": rendered.size,
                    "transparency_flattened": bool(has_alpha and flatten_alpha)})
        if changed:
            doc.install_model(page_index, model)
    if doc.signature(ignore_images=True) != before:
        raise ValueError("Non-image structure changed")
    require_valid(doc)
    output = doc.write(destination)
    checked = Document(output)
    if checked.signature(ignore_images=True) != before:
        raise ValueError("Saved non-image structure changed")
    return {"operation": "compress", "output": str(output), "source_bytes": doc.source.stat().st_size,
        "output_bytes": output.stat().st_size, "page_count": len(checked.pages),
        "non_image_structure_identical": True, "images": records}


def update_style(style, updates):
    if not isinstance(updates, dict):
        raise ValueError("style_updates must be an object")
    for key, value in updates.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
            raise ValueError("Invalid style key")
        if value is not None and (isinstance(value, (list, dict)) or ";" in str(value)):
            raise ValueError("Style values must be scalar and cannot inject extra tokens")
        parts = [p for p in style.split(";") if p and not p.startswith(key + "=")]
        if value is not None:
            value = int(value) if isinstance(value, bool) else value
            parts.append(f"{key}={value}")
        style = ";".join(parts) + ";"
    return style


def patch(doc, patches, destination, page_id):
    require_valid(doc)
    index = doc.page_index(page_id)
    model = copy.deepcopy(doc.models[index])
    by_id = {identifier: (cell, owner) for cell, owner, identifier in cells(model)}
    seen = set()
    if not isinstance(patches, list) or not patches:
        raise ValueError("Patch data must be a nonempty array")
    for item in patches:
        if not isinstance(item, dict) or set(item) - {"id", "label", "style_updates", "geometry"}:
            raise ValueError("Unknown patch field")
        identifier = item.get("id")
        if identifier in seen or identifier not in by_id:
            raise ValueError("Missing or repeated patch id")
        seen.add(identifier)
        cell, owner = by_id[identifier]
        if "label" in item:
            if not isinstance(item["label"], str):
                raise ValueError("label must be a string")
            owner.set("label" if owner is not cell else "value", item["label"])
        if "style_updates" in item:
            cell.set("style", update_style(cell.get("style", ""), item["style_updates"]))
        if "geometry" in item:
            geometry = item["geometry"]
            if not isinstance(geometry, dict) or set(geometry) - {"x", "y", "width", "height"}:
                raise ValueError("Unknown geometry field")
            node = cell.find("mxGeometry")
            if node is None:
                raise ValueError("Cell has no mxGeometry")
            for key, value in geometry.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Geometry must contain finite numbers")
                if key in ("width", "height") and value <= 0:
                    raise ValueError("Width and height must be positive")
                node.set(key, str(value))
    doc.install_model(index, model)
    require_valid(doc)
    output = doc.write(destination)
    require_valid(Document(output))
    return {"operation": "patch", "output": str(output), "page_id": page_id,
        "changed_ids": sorted(seen), "page_count": len(doc.pages)}


def merge_page(doc, snapshot, destination, page_id):
    require_valid(doc)
    require_valid(snapshot)
    if len(snapshot.pages) != 1:
        raise ValueError("Snapshot must contain exactly one page")
    index = doc.page_index(page_id)
    before_other = [ET.tostring(m) for i, m in enumerate(doc.models) if i != index]
    attrs = dict(doc.pages[index].attrib)
    doc.install_model(index, copy.deepcopy(snapshot.models[0]))
    require_valid(doc)
    output = doc.write(destination)
    checked = Document(output)
    if checked.pages[index].attrib != attrs or [ET.tostring(m) for i, m in enumerate(checked.models) if i != index] != before_other:
        raise ValueError("Other pages or target page metadata changed")
    return {"operation": "merge-page", "output": str(output), "page_id": page_id,
        "page_count": len(checked.pages), "other_pages_identical": True, "target_page_metadata_preserved": True}


def export_diagram(source, destination, drawio=None, width=2000, page_index=0, cli_page_base=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError("Export output must be a new file")
    doc = Document(source)
    require_valid(doc)
    if page_index < 0 or page_index >= len(doc.pages):
        raise ValueError("Invalid export page index")
    fmt = destination.suffix[1:].lower()
    if fmt not in ("png", "jpg", "svg", "pdf"):
        raise ValueError("Export format must be png/jpg/svg/pdf")
    executable = drawio or os.environ.get("DRAWIO_PATH") or shutil.which("draw.io") or shutil.which("drawio")
    if not executable:
        candidates = [Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "draw.io" / "draw.io.exe",
            Path("/Applications/draw.io.app/Contents/MacOS/draw.io")]
        executable = next((str(p) for p in candidates if p.is_file()), None)
    if not executable:
        raise ValueError("draw.io Desktop not found; specify --drawio or DRAWIO_PATH")
    version = None
    if cli_page_base is None:
        query = subprocess.run([str(executable), "--version"], capture_output=True, timeout=15, check=False)
        match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", query.stdout.decode("utf-8", errors="replace"))
        if query.returncode or not match:
            raise ValueError("Cannot detect Desktop version; specify --cli-page-base 1 for >=27.0.2 or 0 for older CLI")
        version_tuple = tuple(int(v) for v in match.groups())
        version = ".".join(match.groups())
        cli_page_base = 1 if version_tuple >= (27, 0, 2) else 0
    if cli_page_base not in (0, 1):
        raise ValueError("CLI page base must be 0 or 1")
    destination.parent.mkdir(parents=True, exist_ok=True)
    argv = [str(executable), "--export", "--format", fmt, "--output", str(destination),
        "--border", "24", "--page-index", str(page_index + cli_page_base)]
    if fmt in ("png", "jpg"):
        if width < 100 or width > 10000:
            raise ValueError("Invalid raster export width")
        argv += ["--width", str(width)]
    argv.append(str(source))
    result = subprocess.run(argv, capture_output=True, timeout=60, check=False)
    if result.returncode or not destination.is_file() or destination.stat().st_size == 0:
        raise ValueError("Desktop export failed: " + result.stderr.decode("utf-8", errors="replace")[-2000:])
    return {"operation": "export", "output": str(destination), "format": fmt,
        "bytes": destination.stat().st_size, "page_index": page_index, "cli_page_index": page_index + cli_page_base,
        "desktop_version": version, "renderer": "draw.io Desktop"}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_p = sub.add_parser("inspect"); inspect_p.add_argument("input"); inspect_p.add_argument("--max-file-mib", type=int, default=256)
    compress_p = sub.add_parser("compress"); compress_p.add_argument("input"); compress_p.add_argument("output")
    compress_p.add_argument("--quality", type=int, default=90); compress_p.add_argument("--max-side", type=int, default=0)
    compress_p.add_argument("--flatten-alpha", action="store_true"); compress_p.add_argument("--background", default="#FFFFFF")
    compress_p.add_argument("--force-jpeg", action="store_true"); compress_p.add_argument("--report")
    patch_p = sub.add_parser("patch"); patch_p.add_argument("input"); patch_p.add_argument("patches"); patch_p.add_argument("output")
    patch_p.add_argument("--page-id", required=True); patch_p.add_argument("--report")
    merge_p = sub.add_parser("merge-page"); merge_p.add_argument("input"); merge_p.add_argument("snapshot"); merge_p.add_argument("output")
    merge_p.add_argument("--page-id", required=True); merge_p.add_argument("--report")
    export_p = sub.add_parser("export"); export_p.add_argument("input"); export_p.add_argument("output")
    export_p.add_argument("--drawio"); export_p.add_argument("--width", type=int, default=2000); export_p.add_argument("--page-index", type=int, default=0)
    export_p.add_argument("--cli-page-base", type=int, choices=[0, 1])
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inventory(Document(Path(args.input), args.max_file_mib))
        elif args.command == "compress":
            result = compress(Document(Path(args.input)), Path(args.output), args.quality, args.max_side,
                args.flatten_alpha, args.background, args.force_jpeg)
        elif args.command == "patch":
            patches = json.loads(Path(args.patches).read_text(encoding="utf-8"))
            result = patch(Document(Path(args.input)), patches, Path(args.output), args.page_id)
        elif args.command == "merge-page":
            result = merge_page(Document(Path(args.input)), Document(Path(args.snapshot)), Path(args.output), args.page_id)
        else:
            result = export_diagram(args.input, args.output, args.drawio, args.width, args.page_index, args.cli_page_base)
        if getattr(args, "report", None) or args.command in ("compress", "patch", "merge-page"):
            report_path = Path(args.report or (str(args.output) + ".report.json")).resolve()
            if report_path in (Path(args.input).resolve(), Path(args.output).resolve()):
                raise ValueError("Report path conflicts with diagram")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "inspect" and not result["valid"] else 0
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
