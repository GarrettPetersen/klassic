"""Burn a verified SRT into an existing 1440x1080 Klassic export."""
from pathlib import Path
import subprocess
import sys

from PIL import Image
from klassic.captions import CaptionTrack

RATE = 24
WIDTH, HEIGHT = 1440, 1080


def burn(source, srt, destination):
    captions = CaptionTrack(srt)
    ffmpeg = 'ffmpeg'
    duration = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(source)], text=True).strip())
    decoder = subprocess.Popen(
        [ffmpeg, '-v', 'error', '-i', str(source), '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{WIDTH}x{HEIGHT}', '-r', str(RATE), '-'], stdout=subprocess.PIPE)
    encoder = subprocess.Popen(
        [ffmpeg, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{WIDTH}x{HEIGHT}', '-r', str(RATE), '-i', '-', '-i', str(source),
         '-map', '0:v:0', '-map', '1:a:0', '-t', str(duration), '-r', str(RATE),
         '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '18',
         '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(destination)],
        stdin=subprocess.PIPE)
    frame_size = WIDTH * HEIGHT * 3
    try:
        for frame in range(round(duration * RATE)):
            data = decoder.stdout.read(frame_size)
            if len(data) != frame_size:
                raise RuntimeError(f'Video ended before frame {frame}')
            image = Image.frombytes('RGB', (WIDTH, HEIGHT), data)
            captions.paint(image, frame / RATE)
            encoder.stdin.write(image.tobytes())
            if frame and frame % (RATE * 60) == 0:
                print(f'Captioned {frame / RATE:.0f}s', flush=True)
        encoder.stdin.close()
        if decoder.wait() != 0 or encoder.wait() != 0:
            raise RuntimeError('Caption render failed')
    except BaseException:
        decoder.kill()
        encoder.kill()
        decoder.wait()
        encoder.wait()
        Path(destination).unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: burn_captions.py SOURCE.mp4 CAPTIONS.srt DESTINATION.mp4')
    burn(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
