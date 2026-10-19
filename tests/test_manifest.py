"""Controle van manifest.json en hacs.json."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "custom_components" / "spaarnelanden" / "manifest.json"
HACS = ROOT / "hacs.json"


def test_manifest_fields():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["domain"] == "spaarnelanden"
    assert m["name"] == "Spaarnelanden - Afvalwijzer"
    assert m["version"] == "0.1.3"
    assert m["documentation"] == "https://github.com/Nickhoog/spaarnelanden-afvalwijzer"
    assert m["issue_tracker"] == "https://github.com/Nickhoog/spaarnelanden-afvalwijzer/issues"
    assert m["iot_class"] == "cloud_polling"
    assert m["config_flow"] is True
    assert m["integration_type"] == "service"
    assert m["requirements"] == []
    assert set(m) >= {"name", "codeowners", "documentation", "issue_tracker", "dependencies"}


def test_manifest_key_order():
    """hassfest eist domain, name en daarna alfabetische volgorde."""
    keys = list(json.loads(MANIFEST.read_text(encoding="utf-8")))
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_hacs_json():
    h = json.loads(HACS.read_text(encoding="utf-8"))
    assert h == {"name": "Spaarnelanden - Afvalwijzer", "homeassistant": "2026.10.0", "country": "NL"}


def test_brand_icons():
    """Sinds HA 2026.3 levert een custom integration eigen iconen in brand/."""
    from PIL import Image

    brand = MANIFEST.parent / "brand"
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        with Image.open(brand / name) as img:
            assert img.format == "PNG"
            assert img.size == (size, size)
            assert img.mode == "RGBA"
