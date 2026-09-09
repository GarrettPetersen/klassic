"""Adapt authored mouth drawings to a portrait with a foreground nose."""
from pathlib import Path
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .cels import load_cel, load_transition_library, remove_green_matte
from .motion import CelTransitions
from .project import SHAPES, digest, read_json, write_json


def polygon_mask(size, points):
    mask = Image.new("L", (size[0]*4, size[1]*4))
    ImageDraw.Draw(mask).polygon([(x*4, y*4) for x, y in points], fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def mouth_ink_bounds(cel):
    """Moving mouth rectangle, measured without the surrounding muzzle ink."""
    interior = cel.getchannel("A").filter(ImageFilter.MinFilter(19))
    ink = ImageChops.multiply(cel.convert("L").point(lambda v: 255 if v < 130 else 0), interior)
    bounds = ink.getbbox()
    if bounds is None:
        raise ValueError("Cannot fit mouth outline: drawing has no interior lip ink")
    return bounds


def outline_ellipse(cel, outline):
    """Fit vertically to the mirrored mouth opening, excluding the muzzle."""
    bounds = mouth_ink_bounds(cel)
    cx = outline["center_x"]
    cy = (bounds[1]+bounds[3])/2 + outline["center_y_offset"]
    rx = outline["radius_x"]
    height = bounds[3]-bounds[1]
    ry = height/2 + outline["vertical_padding"] + height*outline["height_padding_ratio"]
    feather = outline["feather"]
    if not all(math.isfinite(v) for v in (cx, cy, rx, ry, feather)) or not 0 < feather < min(rx, ry):
        raise ValueError("Outline oval needs finite coordinates and radii larger than its positive feather")
    return cx, cy, rx, ry


def outline_mask(cel, outline):
    cx, cy, rx, ry = outline_ellipse(cel, outline)
    front = Image.new("L", cel.size)
    front.putdata([round(255*max(0, min(1, (1-math.hypot((x-cx)/rx, (y-cy)/ry))*min(rx, ry)/outline["feather"])))
                   for y in range(cel.height) for x in range(cel.width)])
    # The whole moving-mouth rectangle and its leftward extension retain ink.
    # The oval adds the curved leading lip above/below that rectangle.
    left, top, right, bottom = mouth_ink_bounds(cel)
    ImageDraw.Draw(front).rectangle((0, top, right-1, bottom-1), fill=255)
    return front


def outline_overlay(cel, outline):
    cel = ImageOps.mirror(cel)
    cx, cy, rx, ry = outline_ellipse(cel, outline)
    result = Image.new("RGBA", cel.size, "#dddddd")
    result.alpha_composite(cel)
    tint = Image.new("RGBA", cel.size, (0, 130, 255, 0))
    tint.putalpha(outline_mask(cel, outline).point(lambda v: round(v*.14)))
    result.alpha_composite(tint)
    ImageDraw.Draw(result).ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline=(0, 110, 255), width=3)
    left, top, right, bottom = mouth_ink_bounds(cel)
    draw = ImageDraw.Draw(result)
    draw.rectangle((left, top, right-1, bottom-1), outline=(225, 95, 0), width=2)
    draw.line([(0, top), (left, top)], fill=(225, 95, 0), width=2)
    draw.line([(0, bottom-1), (left, bottom-1)], fill=(225, 95, 0), width=2)
    return result


def mouth_layers(cel, tone, outline):
    """Separate patch coverage from ink; keep its front edge, erase back edges."""
    cel = ImageOps.mirror(cel)
    coverage = cel.getchannel("A")
    gray = cel.convert("L")
    # The authored muzzle fill is the dominant opaque mid-gray, unlike ink,
    # white teeth, or the darker tongue. Derive it per drawing, not per key.
    histogram = gray.histogram(mask=coverage)
    skin = max(range(145, 215), key=lambda value: histogram[value])
    # Preserve interior artwork. Recolor the flat skin and its ink antialiasing.
    values = []
    for value in gray.tobytes():
        if skin-18 <= value <= skin+18:
            values.append(tone)
        elif value < skin-18:
            values.append(min(tone, round(value*tone/skin)))
        else:
            values.append(value)
    color = Image.new("L", cel.size)
    color.putdata(values)
    interior = coverage.filter(ImageFilter.MinFilter(19))
    border = ImageChops.subtract(coverage, interior)
    front = outline_mask(cel, outline)
    visible_border = ImageChops.multiply(border, front)
    keep = ImageChops.lighter(interior, visible_border)
    ink = Image.merge("RGBA", (color, color, color, keep))
    return coverage, ink


class GuestPortrait:
    def __init__(self, spec_path):
        self.spec_path = Path(spec_path).resolve()
        self.spec = read_json(self.spec_path)
        root = self.spec_path.parent
        self.tone = self.spec["skin_tone"]
        raw = remove_green_matte(Image.open(root/self.spec["clean_plate"]).convert("RGB"))
        gray = raw.convert("L")
        candidates = gray.point(lambda v: 255 if 140 <= v <= 230 else 0)
        candidates = ImageChops.multiply(candidates, raw.getchannel("A"))
        for seed in self.spec["skin_seeds"]:
            if candidates.getpixel(tuple(seed)) != 255:
                raise ValueError(f"Skin seed {seed} is not in an unprocessed skin region")
            ImageDraw.floodfill(candidates, tuple(seed), 128)
        skin_mask = candidates.point(lambda v: 255 if v == 128 else 0)
        raw.paste((self.tone,)*3+(255,), (0, 0), skin_mask)
        self.portrait = raw
        self.coverage = raw.getchannel("A")
        nose_mask = polygon_mask(raw.size, self.spec["nose_polygon"])
        self.nose = raw.copy()
        self.nose.putalpha(ImageChops.multiply(self.coverage, nose_mask))
        self.position = tuple(self.spec["mouth_position"])
        self.size = tuple(self.spec["mouth_size"])
        endpoints = {s: root/self.spec["endpoints"]/f"{s}.png" for s in SHAPES}
        cells = {s: load_cel(p) for s, p in endpoints.items()}
        pairs, self.library_hashes = load_transition_library(root/self.spec["transitions"], endpoints, cells["X"].size)
        self.layers = {}
        self.cells = {}
        self.overlays = {}
        for name, cel in list(cells.items())+[(f"{p}-{i+1}", c) for p, frames in pairs.items() for i, c in enumerate(frames)]:
            self.overlays[name] = outline_overlay(cel, self.spec["front_outline"])
            mask, ink = mouth_layers(cel, self.tone, self.spec["front_outline"])
            mask = mask.resize(self.size, Image.Resampling.LANCZOS)
            ink = ink.resize(self.size, Image.Resampling.LANCZOS)
            self.layers[name] = (mask, ink)
            self.cells[name] = self.compose(name)
        self.bank = CelTransitions({s: self.cells[s] for s in SHAPES},
            {p: [self.cells[f"{p}-{i}"] for i in (1, 2)] for p in pairs})

    def compose(self, name):
        skin, ink = self.layers[name]
        # The head coverage decides which patch edges actually meet background.
        # A front lip edge is retained independently, even over the far cheek.
        head = self.coverage.crop((*self.position, self.position[0]+self.size[0], self.position[1]+self.size[1]))
        outside = ImageChops.invert(head.filter(ImageFilter.MinFilter(7)))
        exposed = ImageChops.multiply(ImageChops.subtract(skin, skin.filter(ImageFilter.MinFilter(7))), outside)
        result = self.portrait.copy()
        result.paste((self.tone,)*3+(255,), self.position, skin)
        result.paste((10, 10, 10, 255), self.position, exposed)
        result.alpha_composite(ink, self.position)
        result.alpha_composite(self.nose)
        return result


def review_guest(spec_path, output):
    output = Path(output)
    if output.exists():
        raise ValueError(f"Guest review already exists: {output}")
    portrait = GuestPortrait(spec_path)
    output.mkdir(parents=True)
    portrait.portrait.save(output/"clean-plate.png")
    portrait.nose.save(output/"nose.png")
    portrait.coverage.save(output/"head-coverage.png")
    sheet = Image.new("RGB", (1440, 1140), "#dddddd")
    draw = ImageDraw.Draw(sheet)
    for index, shape in enumerate("XABCDEFGH"):
        img = portrait.cells[shape]
        frame = Image.new("RGBA", img.size, "#dddddd")
        frame.alpha_composite(img)
        crop = frame.crop((420, 270, 1140, 810)).convert("RGB").resize((480, 360), Image.Resampling.LANCZOS)
        x, y = index%3*480, index//3*380
        sheet.paste(crop, (x, y+20))
        draw.text((x+12, y+4), shape, fill="black")
    sheet.save(output/"keys.jpg")
    for name, image in portrait.cells.items():
        image.save(output/f"{name}.png")
    (output/"overlays").mkdir()
    for name, overlay in portrait.overlays.items():
        overlay.save(output/"overlays"/f"{name}.png")
    overlay_sheet = Image.new("RGB", (1254, 1314), "#dddddd")
    draw = ImageDraw.Draw(overlay_sheet)
    for index, shape in enumerate("XABCDEFGH"):
        x, y = index%3*418, index//3*438
        overlay_sheet.paste(portrait.overlays[shape].convert("RGB"), (x, y+20))
        draw.text((x+12, y+4), shape, fill="black")
    overlay_sheet.save(output/"outline-overlay.jpg")
    pairs = sorted(portrait.bank.pairs)
    import json
    (output/"index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Fromm mouth fit</title>
<style>body{font:18px system-ui;background:#ddd;margin:24px}img{max-width:100%;max-height:80vh}button,select{font:inherit;margin:8px}label{margin:12px}</style>
<h1>Fromm: front lip contour and separate nose</h1><p>Outline: fitted oval plus the moving-mouth rectangle and its leftward extension. Blue: oval. Orange: mouth rectangle. Shading: retained outline area.</p>
<select id="pair">'''+''.join(f'<option>{p}</option>' for p in pairs)+'''</select><button id="play">Pause</button><label><input id="slow" type="checkbox">Quarter speed</label><label><input id="overlay" type="checkbox">Show outline guide</label><span id="label"></span><br><img id="frame" alt="Fromm mouth transition">
<script>let pairs='''+json.dumps(pairs)+''',tick=0,playing=true;const pair=document.querySelector('#pair'),frame=document.querySelector('#frame'),label=document.querySelector('#label');function show(){let p=pair.value,seq=[p[0],p[0],p[0],p+'-1',p+'-2',p[1],p[1],p[1],p+'-2',p+'-1'];let n=seq[tick%seq.length];frame.src=(document.querySelector('#overlay').checked?'overlays/':'')+n+'.png';label.textContent=n}pair.onchange=()=>{tick=0;show()};document.querySelector('#overlay').onchange=show;document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'Pause':'Play'};let last=0;function loop(t){if(t-last>(document.querySelector('#slow').checked?400:100)){if(playing){tick++;show()}last=t}requestAnimationFrame(loop)}show();requestAnimationFrame(loop);</script>''')
    write_json(output/"manifest.json", {"spec_sha256": digest(spec_path), "character": portrait.spec["character"],
        "drawings": len(portrait.cells), "source_library": portrait.library_hashes,
        "processing": "Mirrored shared drawings, skin recolor, side/back contour removal, retained front lip contour, head coverage and separate foreground nose."})
    return output/"index.html"
