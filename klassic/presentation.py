"""Map dialogue time to a film with one title sequence inserted between turns."""
def title_at(timeline):
    after = timeline.get('presentation', {}).get('title_after_turn')
    if after is None:
        return 0.0
    turns = timeline['turns']
    matches = [i for i,t in enumerate(turns) if t['id'] == after]
    if len(matches) != 1 or matches[0] == len(turns)-1:
        raise ValueError('Title insertion requires a known non-final turn')
    i = matches[0]
    cut = turns[i]['end'] + turns[i]['pause_after']
    if abs(cut-turns[i+1]['start']) > .002:
        raise ValueError('Title insertion must be at a contiguous turn boundary')
    return cut


def screen_time(at, cut, title_seconds, *, end=False):
    """Keep an interval ending exactly at the cut on the teaser side."""
    follows_title = at > cut or (at == cut and not end)
    return at + (title_seconds if follows_title else 0)
