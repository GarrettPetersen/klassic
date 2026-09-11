"""A deterministic 2D cutout rig: waist, complete arm poses, eyelids and pupil layers.

The inverse mesh keeps the original inked drawings and mouth cels together.
An empty stage fills newly exposed areas; furniture and feet stay fixed.
All coordinates are in the authored master canvas, before camera cropping.
"""
import bisect
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .project import digest, read_json
from .gestures import GestureTrack, ArmLibrary


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


class Channel:
    def __init__(self, keys, duration):
        if not keys or keys[0][0] != 0 or keys[-1][0] != duration:
            raise ValueError("Motion keys must cover the complete dialogue")
        if any(len(k) != 2 or not all(math.isfinite(v) for v in k) for k in keys):
            raise ValueError("Motion keys must be finite time/value pairs")
        if any(a[0] >= b[0] for a, b in zip(keys, keys[1:])):
            raise ValueError("Motion keys must be strictly ordered")
        self.keys, self.starts = keys, [k[0] for k in keys]

    def sample(self, at):
        if not 0 <= at <= self.starts[-1]:
            raise ValueError("Motion sample outside the dialogue")
        i = bisect.bisect_right(self.starts, at)-1
        if i == len(self.keys)-1:
            return self.keys[i][1]
        (a, x), (b, y) = self.keys[i:i+2]
        return x + (y-x)*smooth((at-a)/(b-a))


def rotate(point, pivot, angle):
    radians = math.radians(angle)
    c, s = math.cos(radians), math.sin(radians)
    x, y = point[0]-pivot[0], point[1]-pivot[1]
    return pivot[0]+c*x-s*y, pivot[1]+s*x+c*y


def forward(point, character, state):
    x, y = point
    amount = smooth((650-y)/100)
    leaned = rotate(point, character["waist"], state["lean"])
    return x+amount*(leaned[0]-x), y+amount*(leaned[1]-y)


def arm_point(point, character, state, name):
    bone = character['arms'][name]
    shoulder = bone['shoulder']
    rotated = rotate(point, shoulder, state[name]*bone['degrees'])
    parent = forward(shoulder,character,state)
    leaned = rotate(rotated,shoulder,state['lean'])
    return leaned[0]+parent[0]-shoulder[0], leaned[1]+parent[1]-shoulder[1]



def affine_inverse(map_point):
    origin=map_point((0,0)); x=map_point((1,0)); y=map_point((0,1))
    a,b=x[0]-origin[0],y[0]-origin[0]
    d,e=x[1]-origin[1],y[1]-origin[1]
    determinant=a*e-b*d
    if abs(determinant)<.001:raise ValueError('Degenerate arm transform')
    return (e/determinant,-b/determinant,(b*origin[1]-e*origin[0])/determinant,
            -d/determinant,a/determinant,(d*origin[0]-a*origin[1])/determinant)


def transformed_cutout(source, mask, map_point):
    rect=mask.getbbox()
    if rect is None:raise ValueError('Empty arm mask')
    left,top,right,bottom=rect
    points=[map_point(p) for p in ((left,top),(right,top),(right,bottom),(left,bottom))]
    bounds=(math.floor(min(p[0] for p in points))-2,math.floor(min(p[1] for p in points))-2,
            math.ceil(max(p[0] for p in points))+2,math.ceil(max(p[1] for p in points))+2)
    sprite=source.crop(rect);sprite.putalpha(mask.crop(rect))
    a,b,c,d,e,f=affine_inverse(map_point)
    matrix=(a,b,a*bounds[0]+b*bounds[1]+c-left,d,e,d*bounds[0]+e*bounds[1]+f-top)
    return sprite.transform((bounds[2]-bounds[0],bounds[3]-bounds[1]),Image.Transform.AFFINE,
                            matrix,Image.Resampling.BICUBIC),bounds[:2]


def inverse(point, character, state):
    estimate = point
    for _ in range(4):
        actual = forward(estimate, character, state)
        estimate = estimate[0]+point[0]-actual[0], estimate[1]+point[1]-actual[1]
    return estimate


class PuppetStage:
    def __init__(self, path, timeline, size):
        self.path = Path(path).resolve()
        self.spec = read_json(self.path)
        if self.spec["version"] != 5 or tuple(self.spec["canvas"]) != size:
            raise ValueError("Puppet canvas/version does not match the stage")
        self.size = size
        self.duration = timeline["duration"]
        self.paths = [self.path]
        self.background = self.asset(self.spec["background"]).convert("L")
        performance_path = self.path.parent/self.spec["performance"]
        self.paths.append(performance_path)
        performance = read_json(performance_path)
        if performance["turns"] != [{k: t[k] for k in ("id", "speaker", "start", "end")}
                                    for t in timeline["turns"]]:
            raise ValueError("Performance was authored for different dialogue timing")
        if set(self.spec["characters"]) != {"host", "guest"}:
            raise ValueError("Puppet stage requires both characters")
        self.channels, self.masks, self.eye_masks, self.body_patches = {}, {}, {}, {}
        self.eye_plates,self.arm_libraries,self.gestures,self.chair_fronts,self.body_ink,self.lap_fronts={},{},{},{},{},{}
        for speaker, character in self.spec["characters"].items():
            self.masks[speaker] = self.asset(character["mask"]).convert("L")
            self.body_patches[speaker]=self.asset(character['body_patch']).convert('RGBA')
            self.body_ink[speaker]=self.asset(character['body_ink']).convert('RGBA')
            self.chair_fronts[speaker]=self.asset(character['chair_front']).convert('RGBA')
            self.lap_fronts[speaker]=self.asset(character['lap_front']).convert('RGBA')
            self.eye_plates[speaker]=self.asset(character['eye_plate']).convert('RGBA')
            self.arm_libraries[speaker]={}
            self.gestures[speaker]={}
            for name,bone in character['arms'].items():
                library=ArmLibrary(self.path.parent/bone['library'])
                if library.spec['anatomical_hand']!=bone['anatomical_hand']:
                    raise ValueError('Wrong anatomical hand library assigned to arm')
                self.paths.extend(library.paths)
                self.arm_libraries[speaker][name]=library
                self.gestures[speaker][name]=GestureTrack(performance['gestures'][speaker][name],self.duration,set(library.cels))
            keys = performance["characters"][speaker]
            if set(keys) != {"lean", "blink", "gaze"}:
                raise ValueError("Missing or unknown performance channels")
            self.channels[speaker] = {name: Channel(k, self.duration) for name, k in keys.items()}
            if any(abs(k[1]) > 3 for k in keys["lean"]):
                raise ValueError("Lean exceeds the authored three-degree range")
            for name in ("blink", "gaze"):
                if any(not 0 <= k[1] <= 1 for k in keys[name]):
                    raise ValueError(f"{name} values must be in 0..1")
            self.eye_masks[speaker] = []
            for eye in character["eyes"]:
                mask = Image.new("L", size)
                ImageDraw.Draw(mask).polygon([tuple(p) for p in eye["polygon"]], fill=255)
                self.eye_masks[speaker].append(mask)
            if sorted(b['layer'] for b in character['arms'].values())!=['far','near']:
                raise ValueError('Each character needs one far and one near arm')
            if {b['anatomical_hand'] for b in character['arms'].values()}!={'left','right'}:
                raise ValueError('Each character needs one left and one right hand')
            for bone in character['arms'].values():
                if len(bone['shoulder'])!=2 or abs(bone['degrees'])>3:
                    raise ValueError('Invalid shoulder attachment or gesture range')
        # Shared vertices are computed once per frame so neighboring quads meet.
        self.grids = {}
        for speaker, character in self.spec["characters"].items():
            x0, y0, x1, y1 = character["bounds"]
            self.grids[speaker] = (list(range(x0, x1, 36))+[x1], list(range(y0, y1, 36))+[y1])

    def asset(self, name):
        path = self.path.parent/name
        self.paths.append(path)
        image = Image.open(path)
        if image.size != self.size:
            raise ValueError(f"Puppet asset has wrong size: {path}")
        return image

    def hashes(self):
        return {str(p): digest(p) for p in sorted(set(self.paths))}

    def state(self, speaker, at):
        state={name: channel.sample(at) for name, channel in self.channels[speaker].items()}
        for arm,track in self.gestures[speaker].items():
            pose,amount=track.sample(at)
            state[arm]=amount;state[f'{arm}_pose']=pose
        return state

    def eyes(self, image, speaker, state):
        character = self.spec["characters"][speaker]
        plate=self.eye_plates[speaker]
        image.paste(plate.convert('L'),(0,0),plate.getchannel('A'))
        # A pupil-free base plus separate pupils; never paint over an old pupil.
        for eye, mask in zip(character["pupils"], self.eye_masks[speaker]):
            layer = image.copy()
            draw = ImageDraw.Draw(layer)
            x, y = eye["rest"];radius = eye["radius"]
            target = eye["camera"]
            x += (target[0]-x)*state["gaze"]
            y += (target[1]-y)*state["gaze"]
            draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=12)
            image.paste(layer, (0,0), mask)
        blink = state["blink"]
        # Close upper and lower lids onto a curved seam, leaving the glasses
        # and outer eye ink untouched. There is no dissolve between faces.
        if blink > 0:
            for eye, mask in zip(character["eyes"], self.eye_masks[speaker]):
                left,top,right,bottom = mask.getbbox()
                center = top+(bottom-top)*.57
                layer = Image.new("L",self.size,eye["lid_gray"])
                aperture = Image.new("L",self.size)
                points = [(x,center+(y-center)*(1-blink)) for x,y in eye["polygon"]]
                if blink < .99:
                    ImageDraw.Draw(aperture).polygon(points,fill=255)
                    layer.paste(image,(0,0),aperture)
                seam = []
                for i in range(21):
                    u=i/20
                    x=left+(right-left)*u
                    y=center-3+5*math.sin(math.pi*u)-(bottom-top)*.5*(1-blink)*math.sin(math.pi*u)
                    seam.append((x,y))
                ImageDraw.Draw(layer).line(seam,fill=30,width=2,joint="curve")
                image.paste(layer,(0,0),mask)

    def paint_arm(self,result,speaker,name,state):
        character=self.spec['characters'][speaker]
        bone=character['arms'][name]
        cel,pose=self.arm_libraries[speaker][name].frame(state[f'{name}_pose'])
        if pose['anatomical_hand']!=bone['anatomical_hand']:
            raise ValueError('Arm pose changed anatomical handedness')
        anchor=pose['anchor'];shoulder=bone['shoulder']
        def mapping(p):
            world=(p[0]-anchor[0]+shoulder[0],p[1]-anchor[1]+shoulder[1])
            return arm_point(world,character,state,name)
        arm,offset=transformed_cutout(cel,cel.getchannel('A'),mapping)
        result.paste(arm.convert('L'),offset,arm.getchannel('A'))
        return mapping(pose['cigarette_tip']) if name=='cigarette' else None

    def frame(self, painted, at, mouth_masks):
        result = self.background.copy()
        tips = []
        for speaker, character in self.spec['characters'].items():
            state = self.state(speaker, at)
            source = painted.copy()
            self.eyes(source, speaker, state)
            source = source.convert('RGBA')
            bounds=character['bounds'];left,top,right,bottom=bounds
            original = source.crop(bounds)
            mask = ImageChops.lighter(self.masks[speaker], mouth_masks[speaker])
            original.putalpha(mask.crop(bounds))
            # Repairs are underlays: retained suit ink must never be painted out.
            body = Image.alpha_composite(self.body_patches[speaker].crop(bounds),original)
            body = Image.alpha_composite(body,self.body_ink[speaker].crop(bounds))
            xs, ys = self.grids[speaker]
            vertices = {(x,y): inverse((x,y), character, state) for x in xs for y in ys}
            mesh = []
            for y0, y1 in zip(ys, ys[1:]):
                for x0, x1 in zip(xs, xs[1:]):
                    quad = sum(((vertices[p][0]-left,vertices[p][1]-top) for p in ((x0,y0),(x0,y1),(x1,y1),(x1,y0))), ())
                    mesh.append(((x0-left,y0-top,x1-left,y1-top), quad))
            layer = body.transform(body.size, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)
            far=next(n for n,b in character['arms'].items() if b['layer']=='far')
            near=next(n for n,b in character['arms'].items() if b['layer']=='near')
            tip=self.paint_arm(result,speaker,far,state)
            result.paste(layer.convert('L'),(left,top),layer.getchannel('A'))
            lap=self.lap_fronts[speaker]
            result.paste(lap.convert('L'),(0,0),lap.getchannel('A'))
            chair=self.chair_fronts[speaker]
            result.paste(chair.convert('L'),(0,0),chair.getchannel('A'))
            near_tip=self.paint_arm(result,speaker,near,state)
            if near_tip is not None:tip=near_tip
            if tip is None:raise ValueError('Character has no cigarette tip')
            tips.append((tip[0]/self.size[0],tip[1]/self.size[1]))
        return result,tips
