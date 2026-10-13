"""Le immagini: indice delle sottocartelle e script di download (senza rete: risposte finte)."""
import importlib.util
from pathlib import Path


def _load():
    p = Path(__file__).resolve().parents[1] / "strumenti" / "scarica_immagini.py"
    spec = importlib.util.spec_from_file_location("scarica", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_find_picks_first_image(monkeypatch):
    m = _load()
    fake = {"query": {"pages": {"2": {"index": 2, "title": "File:B.jpg", "imageinfo": [{"mime": "image/jpeg", "thumburl": "u2"}]},
                                "1": {"index": 1, "title": "File:A.jpg", "imageinfo": [{
                                    "mime": "image/jpeg", "thumburl": "u1", "descriptionurl": "d1",
                                    "extmetadata": {"Artist": {"value": "<a>Fan Kuan</a>"},
                                                    "LicenseShortName": {"value": "Public domain"}}}]}}}}
    monkeypatch.setattr(m, "_get", lambda params: fake)
    hit = m.find("Fan Kuan")
    assert hit["title"] == "File:A.jpg" and hit["url"] == "u1" and hit["license"] == "Public domain"


def test_download_writes_slots_and_credits(tmp_path, monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "SLOTS", {"luoghi/city": "q"})
    monkeypatch.setattr(m, "find", lambda q: {"title": "File:X.png", "url": "http://x", "page": "p", "author": "a",
                                              "license": "PD", "mime": "image/png"})

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"\x89PNG"
    monkeypatch.setattr(m.urllib.request, "urlopen", lambda req, timeout=60: R())
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    m.main([])
    assert (tmp_path / "luoghi" / "city.png").read_bytes() == b"\x89PNG"
    assert "File:X.png" in (tmp_path / "CREDITI.txt").read_text(encoding="utf-8")


def test_images_index_includes_subfolders(tmp_path, monkeypatch):
    from engine.web import game
    import os
    (tmp_path / "immagini" / "luoghi").mkdir(parents=True)
    (tmp_path / "immagini" / "luoghi" / "city.jpg").write_bytes(b"x")
    (tmp_path / "immagini" / "Drago.png").write_bytes(b"x")
    assert set(game.images_index(str(tmp_path / "immagini"))) == {"luoghi/city.jpg", "Drago.png"}
