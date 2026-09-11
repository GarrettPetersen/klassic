"""Remove explicitly reviewed extra speech while retaining raw takes and edit provenance."""
import argparse
from pathlib import Path

from klassic.audio import executable, pcm, run, RATE
from klassic.project import digest, read_json, write_json


def edit_source(source, target):
    if target.exists() or target.with_suffix('.json').exists():
        raise ValueError(f'Edited take already exists: {target}')
    metadata = read_json(source.with_suffix('.json'))
    if digest(source) != metadata['audio_sha256']:
        raise ValueError('Source take differs from its recording manifest')
    duration = len(pcm(source))/2/RATE
    return metadata, duration


def publish_edit(temporary, target, metadata, details):
    edited_duration = len(pcm(temporary))/2/RATE
    metadata.update(audio_sha256=digest(temporary),duration=edited_duration,edit=details)
    temporary.replace(target)
    write_json(target.with_suffix('.json'),metadata)
    print(f'{target}: {edited_duration:.3f}s')


def edit_take(source, target, cuts, crossfade=.008):
    metadata, duration = edit_source(source, target)
    intervals = []
    cursor = 0
    for start,end in cuts:
        if not cursor <= start < end <= duration:
            raise ValueError('Cuts must be ordered, non-overlapping, and within the recording')
        if cursor < start:
            intervals.append((cursor,start))
        cursor = end
    if cursor < duration:
        intervals.append((cursor,duration))
    if not cuts or not intervals or any(end-start <= crossfade*2 for start,end in intervals):
        raise ValueError('An edit must retain audio with enough room for each crossfade')
    filters = [f'[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[s{i}]'
               for i,(start,end) in enumerate(intervals)]
    previous = 's0'
    for i in range(1,len(intervals)):
        output = f'j{i}'
        filters.append(f'[{previous}][s{i}]acrossfade=d={crossfade}:c1=tri:c2=tri[{output}]')
        previous = output
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary = target.with_suffix('.partial.wav')
    run([executable('ffmpeg'),'-v','error','-y','-i',source,'-filter_complex',';'.join(filters),
         '-map',f'[{previous}]','-ac','1','-ar',str(RATE),'-c:a','pcm_s16le',temporary])
    publish_edit(temporary,target,metadata,{'source':str(source.resolve()),'source_sha256':digest(source),
                 'removed_intervals_seconds':cuts,'crossfade_seconds':crossfade if len(intervals)>1 else 0})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('target',type=Path)
    parser.add_argument('--cut',type=float,nargs=2,action='append',required=True,metavar=('START','END'))
    args = parser.parse_args()
    edit_take(args.source,args.target,args.cut)
