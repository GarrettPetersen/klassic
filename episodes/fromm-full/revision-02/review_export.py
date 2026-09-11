"""Extract revision checkpoints from the actual encoded film for visual review."""
from pathlib import Path
from PIL import Image, ImageDraw

from klassic.audio import executable, run
from klassic.presentation import screen_time, title_at
from klassic.project import digest, read_json, write_json

build = Path('build/fromm-full-02')
out = build/'production'
out.mkdir(exist_ok=True)
video = build/'episode-captioned.mp4' if (build/'episode-captioned.mp4').is_file() else build/'episode.mp4'
timeline = read_json(build/'timeline.json')
manifest = read_json(build/'episode-manifest.json')
cut = title_at(timeline)
retake = next(t for t in timeline['turns'] if t['id'] == 't015')
guest = next(t for t in timeline['turns'] if t['speaker'] == 'guest')
retake_at = screen_time(retake['start'], cut, manifest['title_seconds'])
guest_at = screen_time(guest['start'], cut, manifest['title_seconds'])
credits_at = timeline['duration']+manifest['title_seconds']
times = [.5, 26.5, 28.5, 32.5, 34.5, guest_at+3, retake_at+1,
         retake_at+8, 520, 954, 1350]+[credits_at+4+8*i for i in range(5)]
sheet = Image.new('RGB', (1920, 1560), (20,20,20))
draw = ImageDraw.Draw(sheet)
frames = []
for i, at in enumerate(times):
    path = out/f'encoded-{i+1:02d}.png'
    run([executable('ffmpeg'), '-v', 'error', '-y', '-ss', str(at),
         '-i', video, '-frames:v', '1', path])
    x, y = i%4*480, i//4*390
    sheet.paste(Image.open(path).resize((480,360)), (x,y))
    draw.text((x+12,y+367), f'{at:.3f} seconds', fill='white')
    frames.append({'file':path.name, 'time':at, 'sha256':digest(path)})
sheet.save(out/'encoded-review.jpg', quality=94)
write_json(out/'encoded-frames.json', {'episode_sha256':digest(video), 'frames':frames})
page = build/'review.html'
html = page.read_text()
if 'id="revision-points"' not in html:
    nav = ('<p id="revision-points">Revision checkpoints: '
           f'<a href="#interview" data-seek="{cut}">Title and music</a> · '
           f'<a href="#interview" data-seek="{guest_at}">Fromm collar and room tone</a> · '
           f'<a href="#interview" data-seek="{retake_at}">Krusty retake</a></p>\n')
    if '<details>' not in html:
        raise ValueError('Review player structure changed')
    page.write_text(html.replace('<details>', nav+'<details>', 1))
print(out/'encoded-review.jpg')
