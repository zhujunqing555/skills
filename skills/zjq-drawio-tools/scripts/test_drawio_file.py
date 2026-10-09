"""Behavioral regression tests using synthetic multi-page diagrams only."""
import base64
import copy
import io
import os
from pathlib import Path
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

from PIL import Image
from drawio_file import Document, inventory, compress, patch, merge_page, parse_xml, cells, IMAGE


def model(label="测试文本", payload=None, standard_uri=False):
    graph = ET.Element("mxGraphModel", {"pageWidth": "850", "pageHeight": "1100"})
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for identifier, x in [("box-1", 50), ("box-2", 290)]:
        cell = ET.SubElement(root, "mxCell", {"id": identifier, "vertex": "1", "parent": "1",
            "value": "", "style": "rounded=1;fillColor=#DAE8DE;strokeColor=#869F90;"})
        ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": "50", "width": "180", "height": "80", "as": "geometry"})
    label_cell = ET.SubElement(root, "mxCell", {"id": "label-1", "vertex": "1", "parent": "1",
        "value": label, "style": "text;html=1;fillColor=none;strokeColor=none;fontFamily=Microsoft YaHei;fontSize=26;"})
    ET.SubElement(label_cell, "mxGeometry", {"x": "60", "y": "60", "width": "160", "height": "60", "as": "geometry"})
    edge = ET.SubElement(root, "mxCell", {"id": "edge-1", "edge": "1", "parent": "1", "source": "box-1", "target": "box-2",
        "style": "endArrow=block;strokeWidth=3;strokeColor=#687E80;"})
    ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
    if payload:
        cell = ET.SubElement(root, "mxCell", {"id": "picture", "vertex": "1", "parent": "1",
            "style": "shape=image;image=data:image/png" + (";base64," if standard_uri else ",") + payload + ";imageAspect=1;"})
        ET.SubElement(cell, "mxGeometry", {"x": "50", "y": "160", "width": "200", "height": "200", "as": "geometry"})
    return graph


def save(path, first, second=None):
    root = ET.Element("mxfile", {"host": "Electron", "custom": "keep-me"})
    page = ET.SubElement(root, "diagram", {"id": "p1", "name": "第一页", "extra": "preserve"})
    page.append(first)
    if second is not None:
        page = ET.SubElement(root, "diagram", {"id": "p2", "name": "第二页"})
        # Use draw.io's actual URI-encoded + raw DEFLATE + base64 page format.
        text = urllib.parse.quote(ET.tostring(second, encoding="unicode"), safe="~()*!.'")
        compressor = zlib.compressobj(wbits=-15)
        page.text = base64.b64encode(compressor.compress(text.encode()) + compressor.flush()).decode()
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


class FileOperations(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(os.environ.get('ZJQ_TEST_TMPDIR', tempfile.gettempdir())).resolve()
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=self.temp_root)
        self.folder = Path(self.tmp.name)
        image = Image.effect_noise((192, 192), 40).convert("RGB")
        data = io.BytesIO(); image.save(data, format="PNG")
        self.payload = base64.b64encode(data.getvalue()).decode()
        self.source = self.folder / "源文件无后缀"
        save(self.source, model(payload=self.payload, standard_uri=True), model("第二页 z<sup>ax</sup>"))

    def tearDown(self):
        self.assertEqual(self.folder.resolve().parent, self.temp_root)
        self.tmp.cleanup()

    def output(self, name):
        return self.folder / (name + ".drawio")

    def test_compressed_page_inventory(self):
        data = inventory(Document(self.source))
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["pages"]), 2)
        self.assertEqual(data["pages"][0]["bound_edges"], 1)
        self.assertEqual(data["pages"][1]["independent_text"], 1)

    def test_jpeg_conversion_keeps_non_image_structure_and_both_pages(self):
        original_bytes = self.source.read_bytes()
        before = Document(self.source).signature(ignore_images=True)
        report = compress(Document(self.source), self.output("jpg"), force_jpeg=True)
        checked = Document(self.output("jpg"))
        self.assertEqual(checked.signature(ignore_images=True), before)
        self.assertEqual(len(checked.pages), 2)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        picture = next(c for c, _, i in cells(checked.models[0]) if i == "picture")
        match = IMAGE.search(picture.get("style"))
        self.assertEqual(match["kind"], "jpeg")
        self.assertNotIn(";base64,", picture.get("style"))
        with Image.open(io.BytesIO(base64.b64decode(match["body"]))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (192, 192))
        self.assertTrue(report["non_image_structure_identical"])

    def test_transparency_preserved_by_default(self):
        image = Image.new("RGBA", (100, 100), (100, 150, 180, 90))
        data = io.BytesIO(); image.save(data, format="PNG")
        save(self.source, model(payload=base64.b64encode(data.getvalue()).decode()))
        compress(Document(self.source), self.output("alpha"), force_jpeg=True)
        checked = Document(self.output("alpha"))
        picture = next(c for c, _, i in cells(checked.models[0]) if i == "picture")
        match = IMAGE.search(picture.get("style"))
        self.assertEqual(match["kind"], "png")
        with Image.open(io.BytesIO(base64.b64decode(match["body"]))) as checked_image:
            self.assertEqual(checked_image.convert("RGBA").getpixel((20, 20))[3], 90)

    def test_explicit_alpha_flattening_uses_selected_background(self):
        image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        data = io.BytesIO(); image.save(data, format="PNG")
        save(self.source, model(payload=base64.b64encode(data.getvalue()).decode()))
        compress(Document(self.source), self.output("flat"), flatten_alpha=True, background="#F1F6FA", force_jpeg=True)
        picture = next(c for c, _, i in cells(Document(self.output("flat")).models[0]) if i == "picture")
        with Image.open(io.BytesIO(base64.b64decode(IMAGE.search(picture.get("style"))["body"]))) as checked:
            self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(checked.getpixel((20, 20)), (241, 246, 250))))

    def test_snapshot_merges_only_requested_page(self):
        snapshot = self.output("snapshot")
        save(snapshot, model("修改后的独立文字"))
        before = Document(self.source)
        report = merge_page(Document(self.source), Document(snapshot), self.output("merged"), "p1")
        after = Document(self.output("merged"))
        self.assertEqual(ET.tostring(before.models[1]), ET.tostring(after.models[1]))
        self.assertEqual(before.pages[0].attrib, after.pages[0].attrib)
        self.assertTrue(report["other_pages_identical"])
        self.assertIn("修改后的独立文字", ET.tostring(after.models[0], encoding="unicode"))

    def test_patch_preserves_other_page_and_edge_bindings(self):
        before = Document(self.source)
        patches = [{"id": "label-1", "label": "新的文本"}, {"id": "box-2", "geometry": {"x": 310, "width": 190},
            "style_updates": {"strokeWidth": 2.4}}]
        patch(Document(self.source), patches, self.output("patch"), "p1")
        after = Document(self.output("patch"))
        self.assertEqual(ET.tostring(before.models[1]), ET.tostring(after.models[1]))
        edge = next(c for c, _, i in cells(after.models[0]) if i == "edge-1")
        self.assertEqual((edge.get("source"), edge.get("target")), ("box-1", "box-2"))
        label = next(c for c, _, i in cells(after.models[0]) if i == "label-1")
        self.assertTrue(label.get("style").startswith("text;"))

    def test_unknown_patch_fails_without_output(self):
        with self.assertRaises(ValueError):
            patch(Document(self.source), [{"id": "box-1", "label": "one"}, {"id": "unknown", "label": "two"}], self.output("bad"), "p1")
        self.assertFalse(self.output("bad").exists())

    def test_output_refuses_original_and_existing(self):
        doc = Document(self.source)
        with self.assertRaises(ValueError):
            doc.write(self.source)
        target = self.output("existing"); target.write_text("retain me")
        with self.assertRaises(FileExistsError):
            doc.write(target)
        self.assertEqual(target.read_text(), "retain me")

    def test_wrapped_object_id_is_valid_and_label_updates_owner(self):
        graph = model()
        root = graph.find("root")
        wrapped = ET.SubElement(root, "object", {"id": "wrapped", "label": "旧值"})
        cell = ET.SubElement(wrapped, "mxCell", {"vertex": "1", "parent": "1", "style": "text;"})
        ET.SubElement(cell, "mxGeometry", {"x": "50", "y": "300", "width": "200", "height": "50", "as": "geometry"})
        save(self.source, graph)
        self.assertTrue(inventory(Document(self.source))["valid"])
        patch(Document(self.source), [{"id": "wrapped", "label": "新值"}], self.output("wrapped"), "p1")
        self.assertEqual(Document(self.output("wrapped")).models[0].find("root/object").get("label"), "新值")

    def test_invalid_topology_is_reported_and_not_rewritten(self):
        graph = model()
        graph.find("root/mxCell[@id='edge-1']").set("target", "missing")
        save(self.source, graph)
        self.assertFalse(inventory(Document(self.source))["valid"])
        with self.assertRaises(ValueError):
            compress(Document(self.source), self.output("invalid"))
        self.assertFalse(self.output("invalid").exists())

    def test_external_image_reference_is_not_downloaded(self):
        graph = model()
        graph.find("root/mxCell[@id='box-2']").set("style", "shape=image;image=https://invalid.example/evidence.png;")
        save(self.source, graph)
        before = Document(self.source).signature()
        compress(Document(self.source), self.output("external"))
        self.assertEqual(Document(self.output("external")).signature(), before)

    def test_xml_entity_declarations_are_refused(self):
        with self.assertRaises(ValueError):
            parse_xml(b'<!DOCTYPE mxfile [<!ENTITY a "oops">]><mxfile>&a;</mxfile>')


if __name__ == "__main__":
    unittest.main()
