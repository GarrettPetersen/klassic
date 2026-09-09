"""Prepare generated green-screen atlases for ordinary alpha compositing."""
from itertools import combinations
from pathlib import Path

from PIL import Image

from .project import SHAPES, digest, read_json, write_json


def extract_cels(atlas_path, output):
    """Slice the documented 3×3 Rhubarb layout; remove the green matte only."""
    output = Path(output)
    if output.exists():
        raise ValueError(f"Cel output already exists: {output}")
    source = Image.open(atlas_path).convert("RGB")
    if source.width != source.height or source.width % 3:
        raise ValueError("Atlas must be square with dimensions divisible by three")
    rgba = remove_green_matte(source)
    size = source.width // 3
    cells = {}
    for index, shape in enumerate("ABCDEFGHX"):
        x, y = index % 3 * size, index // 3 * size
        cel = rgba.crop((x, y, x+size, y+size))
        box = cel.getchannel("A").getbbox()
        if not box or min(box[:2]) < 4 or max(box[2:]) > size-4:
            raise ValueError(f"Cel {shape} must have ink and clear margins")
        cells[shape] = cel
    assert set(cells) == SHAPES
    output.mkdir(parents=True)
    for shape, cel in cells.items():
        cel.save(output / f"{shape}.png")
    write_json(output / "source.json", {"atlas_sha256": digest(atlas_path),
        "layout": "ABCDEFGHX, row-major 3x3", "processing": "Green matte removed; grayscale spill correction; no mouth redrawing.",
        "cels": {shape: digest(output / f"{shape}.png") for shape in cells}})


def remove_green_matte(source):
    """Remove a chroma background without changing the drawn geometry."""
    rgba = Image.new("RGBA", source.size)
    pixels = []
    for r, g, b in source.getdata():
        excess = max(0, g - max(r, b))
        alpha = 0 if excess > 60 else 255 - excess
        gray = min(255, round((r+b)*255/(2*alpha))) if alpha else 0
        pixels.append((gray, gray, gray, alpha))
    rgba.putdata(pixels)
    return rgba


def load_cel(path, size=None):
    cel = Image.open(path)
    if cel.mode != "RGBA" or cel.getchannel("A").getextrema() != (0, 255):
        raise ValueError(f"{path} must have transparent and opaque pixels")
    if size is not None and cel.size != size:
        raise ValueError(f"{path} must use the common {size} canvas")
    return cel


def ink_bounds(cel):
    # Ignore faint antialiasing fringes when registering a cel.
    box = cel.getchannel("A").point(lambda value: 255 if value >= 128 else 0).getbbox()
    if not box:
        raise ValueError("Cel has no opaque artwork")
    return box


def register_cel(cel, source, target, progress):
    """One uniform offline scale plus translation. Never deform ink or teeth."""
    box = ink_bounds(cel)
    if box[0] < 4 or box[1] < 4 or box[2] > cel.width-4 or box[3] > cel.height-4:
        raise ValueError("Generated cel touches its tile edge; inspect the atlas layout")
    a, b = ink_bounds(source), ink_bounds(target)
    expected = [round((1-progress)*x+progress*y) for x,y in zip(a,b)]
    scale = (expected[2]-expected[0])/(box[2]-box[0])
    scaled = cel.resize((round(cel.width*scale),round(cel.height*scale)), Image.Resampling.LANCZOS)
    bounds = ink_bounds(scaled)
    offset = (expected[0]-bounds[0], expected[1]-bounds[1])
    positioned = tuple(bounds[i]+offset[i%2] for i in range(4))
    if positioned[0] < 4 or positioned[1] < 4 or positioned[2] > source.width-4 or positioned[3] > source.height-4:
        raise ValueError("Registered cel would be clipped; fix the drawing")
    canvas = Image.new("RGBA", source.size)
    canvas.paste(scaled, offset)
    return canvas, {"scale": scale, "offset": list(offset)}


def bake_transitions(spec_path, output):
    """Extract middle columns from explicitly mapped 4x4 drawing sheets."""
    spec_path, output = Path(spec_path).resolve(), Path(output)
    if output.exists():
        raise ValueError(f"Transition output already exists: {output}")
    spec = read_json(spec_path)
    if spec["version"] != 1:
        raise ValueError("Unsupported transition production spec")
    expected = {"".join(pair) for pair in combinations(sorted(SHAPES), 2)}
    pairs = [pair for atlas in spec["atlases"] for pair in atlas["pairs"] if pair is not None]
    if len(pairs) != 36 or set(pairs) != expected:
        raise ValueError("Production spec must include every pair exactly once")
    endpoint_dir = spec_path.parent / spec["endpoints"]
    endpoints = {s: load_cel(endpoint_dir/f"{s}.png") for s in sorted(SHAPES)}
    size = endpoints["X"].size
    if any(cel.size != size for cel in endpoints.values()):
        raise ValueError("Endpoints must share a canvas")
    cells, registration, atlas_hashes = {}, {}, {}
    for atlas in spec["atlases"]:
        if len(atlas["pairs"]) != 4:
            raise ValueError("Each 4x4 atlas must contain four transition rows")
        path = spec_path.parent / atlas["file"]
        raw = Image.open(path).convert("RGB")
        if raw.width != raw.height:
            raise ValueError(f"Transition atlas {path} must be square")
        sheet = remove_green_matte(raw)
        atlas_hashes[atlas["file"]] = digest(path)
        for row, pair in enumerate(atlas["pairs"]):
            if pair is None:
                continue
            for col in (1,2):
                rect = tuple(round(v*sheet.width/4) for v in (col,row,col+1,row+1))
                cel = sheet.crop(rect)
                name = f"{pair}-{col}"
                cells[name], registration[name] = register_cel(cel,endpoints[pair[0]],endpoints[pair[1]],col/3)
    # Validate all drawings before creating the deliverable directory.
    output.mkdir(parents=True)
    for name, cel in cells.items():
        cel.save(output/f"{name}.png")
    manifest = {"version":1, "canvas":list(size), "inbetweens_per_pair":2,
        "processing":"Green matte removal; grayscale spill correction; uniform scale and top/left registration once at bake time. No local warping or blending.",
        "spec_sha256":digest(spec_path), "atlas_sha256":atlas_hashes,
        "endpoint_sha256":{s:digest(endpoint_dir/f"{s}.png") for s in endpoints},
        "pairs":{p:[f"{p}-1.png",f"{p}-2.png"] for p in sorted(expected)},
        "cel_sha256":{f"{n}.png":digest(output/f"{n}.png") for n in cells},
        "registration":registration}
    write_json(output/"library.json",manifest)
    return output/"library.json"


def load_transition_library(path, endpoint_paths, size):
    path = Path(path)
    library = read_json(path)
    if library["version"] != 1 or library["inbetweens_per_pair"] != 2:
        raise ValueError("Unsupported mouth transition library")
    if set(library["endpoint_sha256"]) != SHAPES:
        raise ValueError("Transition library must identify all endpoints")
    for shape, filename in endpoint_paths.items():
        if digest(filename) != library["endpoint_sha256"][shape]:
            raise ValueError(f"Transition endpoint {shape} changed; rebuild its transition library")
        load_cel(filename, tuple(library["canvas"]))
    pairs = {}
    hashes = library["cel_sha256"]
    names = [name for frames in library["pairs"].values() for name in frames]
    if set(names) != set(hashes) or len(names) != len(set(names)):
        raise ValueError("Transition cel hash inventory must match the unique drawing paths")
    for pair, filenames in library["pairs"].items():
        frames = []
        for filename in filenames:
            file = path.parent/filename
            if digest(file) != hashes[filename]:
                raise ValueError(f"Transition cel {filename} changed after baking")
            frames.append(load_cel(file, tuple(library["canvas"])).resize(size, Image.Resampling.LANCZOS))
        pairs[pair] = frames
    return pairs, {"library_sha256":digest(path), "cel_sha256":hashes}
