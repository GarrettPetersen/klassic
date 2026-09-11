"""Deliberately timed, discrete hand drawings with short articulated transitions."""
import bisect
import math
from pathlib import Path

from .cels import load_cel
from .project import read_json


class GestureTrack:
    def __init__(self, events, duration, poses):
        self.events=events
        self.starts=[]
        previous=0
        for event in events:
            start,end=event['start'],event['end']
            if not (math.isfinite(start) and math.isfinite(end) and previous<=start<end<=duration):
                raise ValueError('Gestures must be ordered, nonoverlapping and inside the dialogue')
            keys=event['keys']
            if len(keys)<2 or any(len(key)!=3 for key in keys):
                raise ValueError('Gesture needs at least two time/pose/amount keys')
            for key in keys:
                if key[1] not in poses or not math.isfinite(key[0]) or not 0<=key[2]<=1:
                    raise ValueError('Invalid gesture pose or motion amount')
            if keys[0][0]!=0 or abs(keys[-1][0]-(end-start))>.001:
                raise ValueError('Gesture keys must cover the complete event')
            if keys[0][1]!='relaxed' or keys[0][2]!=0:
                raise ValueError('A gesture must begin in its rest pose')
            if keys[-1][1]!='relaxed' or keys[-1][2]!=0:
                raise ValueError('A gesture must return to its rest pose')
            if any(a[0]>=b[0] for a,b in zip(keys,keys[1:])):
                raise ValueError('Gesture keys must be strictly ordered')
            self.starts.append(start);previous=end

    def sample(self, at):
        index=bisect.bisect_right(self.starts,at)-1
        if index<0 or at>=self.events[index]['end']:
            return 'relaxed',0.0
        event=self.events[index];local=at-event['start'];keys=event['keys']
        i=bisect.bisect_right([k[0] for k in keys],local)-1
        a,pose,value=keys[i]
        if i==len(keys)-1:return pose,value
        b,_,target=keys[i+1]
        u=max(0,min(1,(local-a)/(b-a)));u=u*u*(3-2*u)
        # The drawing switches at an authored key; only joint motion interpolates.
        return pose,value+(target-value)*u


class ArmLibrary:
    def __init__(self,path):
        path=Path(path)
        self.paths=[path]
        self.spec=read_json(path)
        if self.spec['version']!=2 or 'relaxed' not in self.spec['poses']:
            raise ValueError('Arm library requires a rest pose')
        hand=self.spec['anatomical_hand']
        if hand not in ('left','right'):
            raise ValueError('Arm library must identify an anatomical left or right hand')
        curve=self.spec['gray_curve']
        if len(curve)!=256 or any(type(v)!=int or not 0<=v<=255 for v in curve) or any(a>b for a,b in zip(curve,curve[1:])):
            raise ValueError('Arm palette must be a monotonic 256-entry grayscale curve')
        self.cels={}
        for name,pose in self.spec['poses'].items():
            if pose['anatomical_hand']!=hand or pose['digits']!=4:
                raise ValueError('Arm pose changed handedness or digit count')
            file=path.parent/pose['file'];self.paths.append(file)
            cel=load_cel(file,tuple(self.spec['canvas']))
            anchor=pose['anchor']
            if len(anchor)!=2 or not 0<=anchor[0]<cel.width or not 0<=anchor[1]<cel.height:
                raise ValueError('Shoulder anchor is outside its cel')
            self.cels[name]=cel.point(curve*3+list(range(256)))

    def frame(self, pose):
        return self.cels[pose],self.spec['poses'][pose]
