"""The image worker runs without the product package installed."""
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from superlocalmemory.runtimes import media_image_ops


def test_image_prepare_caption_in_standalone_worker(tmp_path):
    module = Path(__file__).parents[2] / "src/superlocalmemory/runtimes/media_image_ops.py"
    script = tmp_path / "standalone.py"
    script.write_text('''import sys, importlib.util, types
from pathlib import Path
sys.modules["superlocalmemory"] = None
sys.modules["imagehash"] = types.SimpleNamespace(phash=lambda _: "test")
spec = importlib.util.spec_from_file_location("ops", sys.argv[1])
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)
root = Path(sys.argv[2])
class Image:
    width, height, format = 64, 32, "PNG"
    def convert(self, mode): return Image()
    def thumbnail(self, size): pass
    def getdata(self): return [(0, 0, 255)] * 2048
    def close(self): pass
ops._open_checked = lambda _: Image()
ops._load_upright = lambda image: (image, {}, None)
ops._encode_original = lambda *args: b"original"
ops._encode_thumb = lambda *args: b"thumbnail"
result = ops.prepare_image(str(root / "blue.png"), str(root))
assert "blue (100%)" in result["visual_summary"]
assert "64 by 32" in result["visual_summary"]
''')
    result = subprocess.run([sys.executable, "-I", str(script), str(module), str(tmp_path)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_offline_subject_caption_includes_confident_objects_only(monkeypatch):
    observations = [
        SimpleNamespace(identifier=lambda: "bicycle", confidence=lambda: .93),
        SimpleNamespace(identifier=lambda: "motorcycle", confidence=lambda: .2),
    ]
    request = SimpleNamespace(results=lambda: observations)
    factory = SimpleNamespace(alloc=lambda: SimpleNamespace(init=lambda: request))
    handler = SimpleNamespace(performRequests_error_=lambda *args: (True, None))
    vision = SimpleNamespace(VNClassifyImageRequest=factory,
                             VNImageRequestHandler=SimpleNamespace(alloc=lambda: SimpleNamespace(
                                 initWithURL_options_=lambda *args: handler)))
    foundation = SimpleNamespace(NSURL=SimpleNamespace(fileURLWithPath_=lambda path: path))
    monkeypatch.setattr(media_image_ops.sys, "platform", "darwin")
    monkeypatch.setattr(media_image_ops.importlib, "import_module",
                         lambda name: vision if name == "Vision" else foundation)
    caption = media_image_ops._apple_subjects("fixture.png")
    assert "bicycle" in caption and "motorcycle" not in caption
