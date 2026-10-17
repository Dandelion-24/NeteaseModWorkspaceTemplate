"""Headless adapter to the pinned upstream PixelArtConverter; no artwork drawing."""
import importlib.util
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load_core():
    tools = HERE.parent
    resources = json.loads((tools / 'manifests/resources.json').read_text(encoding='utf-8'))['resources']
    resource = next(row for row in resources if row['id'] == 'pixel')
    location = tools.parent / resource['destination']
    for row in resource['files']:
        path = location / row['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('Pixel source is not ready. Run python dev_tools/prepare_workspace.py --tools pixel --fetch')
    spec = importlib.util.spec_from_file_location('pixel_art_converter_core', location / 'core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core

def convert(source, destination, palette, crop=None, size=(16, 16)):
    from PIL import Image
    core = load_core()
    with Image.open(source) as original:
        image = original.convert('RGBA')
        if crop:
            box = tuple(round(v * image.size[i % 2]) for i, v in enumerate(crop))
            image = image.crop(box)
        result = core.make_pixel_art(image, size[0], size[1], len(palette), False, False, False,
                                     fixed_palette=palette)
    result.save(destination)
    return result
