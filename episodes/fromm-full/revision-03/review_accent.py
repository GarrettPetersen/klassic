"""Build a listening page from the measured accent reports."""
import html
import os
from pathlib import Path
from urllib.parse import quote
from klassic.project import read_json

ROOT=Path(__file__).resolve().parents[3]
BUILD=ROOT/'build/fromm-motion-test'
report=read_json(BUILD/'accent-report.json')
other=read_json(BUILD/'accent-report-8s.json')
comparisons={s['id']:s for s in other['samples']}
rows=[]
for sample in sorted(report['samples'],key=lambda s:s['worst_window_distance'],reverse=True):
    window=max(sample['windows'],key=lambda w:w['distance'])
    audio=quote(os.path.relpath(ROOT/sample['file'],BUILD),safe='/')
    rows.append(f"""<tr><td>{html.escape(sample['id'])}</td><td>{sample['worst_window_distance']:.5f}</td>
<td>{comparisons[sample['id']]['worst_window_distance']:.5f}</td><td>
<audio controls preload="none" src="{audio}#t={window['start']:.3f},{window['end']:.3f}"></audio>
<div>6-second review window: {window['start']:.2f}–{window['end']:.2f}s within the take</div></td></tr>""")
(BUILD/'accent-review.html').write_text(f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Krusty accent review</title><style>body{{background:#181818;color:#eee;font:16px/1.5 system-ui;max-width:1100px;margin:36px auto;padding:0 24px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #555}}a{{color:#adcfff}}audio{{width:360px}}td div{{font-size:12px;color:#bbb}}</style>
<h1>Krusty accent review</h1><p><strong>Experimental listening aid. Automatic rejection is disabled.</strong></p>
<p>The original reported drift at 4:14 barely exceeds the highest provisional comparison at six seconds, and falls below several comparisons with eight-second windows. The replacement scores farther from the baseline. These results do not establish which take sounds better.</p>
<p>Higher means farther from the baseline in accent-model embedding space. This can reflect pronunciation, performance, noise or synthesis artifacts. All tested windows receive the model's broad “us” label; it has no Texas label. Baseline and holdout examples have not each been individually approved by a listener.</p>
<p><a href="accent-report.json">6-second evidence</a> · <a href="accent-report-8s.json">8-second sensitivity test</a> · <a href="https://huggingface.co/Jzuluaga/accent-id-commonaccent_ecapa">Model card</a></p>
<table><thead><tr><th>Take</th><th>6s worst</th><th>8s worst</th><th>Listen with context</th></tr></thead><tbody>{''.join(rows)}</tbody></table></html>""")
