"""Export the canonical arrival scene and registered character sources."""
from pathlib import Path
import argparse
from klassic.production import bundle_project

ROOT=Path(__file__).resolve().parents[2]
def build(out):
    return bundle_project(ROOT/'assets/production/scenes/arrival/project.json',ROOT/'assets/production',out,draft=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'build/arrival');print(build(p.parse_args().out))
