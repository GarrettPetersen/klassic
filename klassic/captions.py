"""Reusable, seekable SRT overlay for finished picture renders."""
import bisect
import re
from pathlib import Path
from PIL import ImageDraw, ImageFont

TIME = re.compile(r"(\d+):(\d\d):(\d\d),(\d\d\d) --> (\d+):(\d\d):(\d\d),(\d\d\d)")


def read_srt(path):
    def seconds(h,m,s,ms):return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
    cues=[]
    for number,block in enumerate(Path(path).read_text().strip().split('\n\n'),1):
        lines=block.splitlines()
        if len(lines)<3 or lines[0]!=str(number) or not (match:=TIME.fullmatch(lines[1])):
            raise ValueError(f'Invalid SRT block {number}')
        values=match.groups();start,end=seconds(*values[:4]),seconds(*values[4:])
        if start<0 or end<=start or (cues and start<cues[-1][1]):
            raise ValueError('SRT cues must be positive and ordered without overlaps')
        cues.append((start,end,'\n'.join(lines[2:])))
    return cues


class CaptionTrack:
    def __init__(self,path):
        self.cues=read_srt(path)
        self.starts=[c[0] for c in self.cues]
        self.font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',35)

    def paint(self,image,at):
        index=bisect.bisect_right(self.starts,at)-1
        if index<0 or at>=self.cues[index][1]:return
        text=self.cues[index][2]
        draw=ImageDraw.Draw(image,'RGBA')
        box=draw.multiline_textbbox((0,0),text,font=self.font,spacing=7,align='center')
        band_height=box[3]-box[1]+38
        draw.rectangle((0,image.height-band_height-10,image.width,image.height),fill=(18,18,18,242))
        draw.multiline_text((image.width/2,image.height-band_height+9),text,font=self.font,
                            fill=(242,242,242,255),anchor='ma',align='center',spacing=7)
