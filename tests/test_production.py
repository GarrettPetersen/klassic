import base64
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from klassic.production import import_character,export_character,record_review,check_reviews,register_revision,apply_review_bundle,load_catalog,project_review_data
from klassic.reviews import character_reviews,project_reviews,review_states,signature
from klassic.authoring import apply_registration,prepare_import,apply_import
from klassic.project import digest,write_json,read_json

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        image=Image.new('RGBA',(9,13),(40,80,120,127));image.putpixel((4,6),(1,2,3,255));image.save(self.root/'body.png')
        asset={'file':'body.png','sha256':digest(self.root/'body.png'),'size':[9,13],'position':[2,3]}
        self.spec={'version':1,'id':'example','origin':[0,0],'fps':24,'initial_state':'seated','drawings':{k:dict(asset) for k in ['body','X','A','open','closed']},
            'poses':{'sit':{'layers':[{'drawing':'body','z':20}],'anchors':{'neck':[3,4]},'attachments':{},'contacts':[]}},
            'states':{'seated':{'pose':'sit','idle':'idle','activity':'seated','view':'right'}},'activities':{'seated':{'label':'Seated','views':['right']}},
            'actions':{'idle':{'from':'seated','to':'seated','loop':True,'frames':[{'pose':'sit','ticks':24}]}},
            'overlays':{'mouth':{'z':50,'drawings':{'X':'X','A':'A'}},'eyes':{'z':60,'drawings':{'open':'open','closed':'closed'}}}}
        write_json(self.root/'character.json',self.spec)
        self.catalog=import_character(self.root/'character.json',self.root/'body.png',self.root/'author','Fixture character.')
    def approve(self):
        c,s=load_catalog(self.catalog)
        for subject in character_reviews(c,s):record_review(self.catalog,subject,'approved','Test reviewer','Fixture proof only',self.root/'body.png')
    def edit(self,fn):
        p=self.catalog.parent/'character.json';s=read_json(p);fn(s);write_json(p,s)
    def test_export_preserves_pixels_and_is_deterministic(self):
        self.approve();a=export_character(self.catalog,self.root/'one');b=export_character(self.catalog,self.root/'two');self.assertEqual(a.read_bytes(),b.read_bytes())
        spec=read_json(a);asset=spec['drawings']['body'];x,y,w,h=asset['region']
        with Image.open(a.parent/asset['file']) as atlas,Image.open(self.root/'body.png') as source:self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),source.tobytes())
    def test_drawings_faces_and_timing_are_separate_acceptance_units(self):
        self.approve();self.edit(lambda s:s['actions']['idle']['frames'][0].update(ticks=30));states=check_reviews(self.catalog)
        self.assertEqual(states['clip:idle'],'stale');self.assertEqual(states['pose:sit'],'approved');self.assertEqual(states['drawing:body'],'approved')
        Image.new('RGBA',(9,13),(0,0,0,255)).save(self.catalog.parent/'drawings/A.png')
        with self.assertRaisesRegex(ValueError,'Source changed'):check_reviews(self.catalog)
        register_revision(self.catalog);states=check_reviews(self.catalog)
        self.assertEqual(states['face:sit:eyes%3Dopen:mouth%3DA'],'stale');self.assertEqual(states['face:sit:eyes%3Dopen:mouth%3DX'],'approved')
    def test_pose_approval_does_not_approve_faces_or_transition(self):
        record_review(self.catalog,'pose:sit','approved','Fixture','Inspected body only.',self.root/'body.png')
        self.assertEqual(check_reviews(self.catalog)['clip:idle'],'unreviewed')
        with self.assertRaisesRegex(ValueError,'requires'):export_character(self.catalog,self.root/'out')
        export_character(self.catalog,self.root/'draft',draft=True)
    def test_scene_placement_and_performance_timing_invalidate_project_reviews(self):
        _,s=load_catalog(self.catalog);project={'scenes':{'room':{'actors':[{'id':'host','character':'example','position':[0,0]}]}},'story':{},'takes':{},'performance':[{'at':0,'type':'caption','text':'Hi'}]}
        manifest=project_reviews(project,{'example':s});records={k:{'decision':'approved','signature':v['signature']} for k,v in manifest.items()}
        project['performance'][0]['at']=1;states=review_states(records,project_reviews(project,{'example':s}));self.assertEqual(states['scene:room'],'approved');self.assertEqual(states['performance'],'stale')
        project['scenes']['room']['actors'][0]['position']=[10,0];self.assertEqual(review_states(records,project_reviews(project,{'example':s}))['scene:room'],'stale')
    def test_invalid_bundle_never_partially_writes_reviews(self):
        before=self.catalog.read_bytes();bundle=self.root/'reviews.json';write_json(bundle,{'version':2,'character':'example','reviews':[{'subject':'pose:sit','signature':'wrong','proof':'data:image/png;base64,'}]})
        with self.assertRaisesRegex(ValueError,'different source'):apply_review_bundle(self.catalog,bundle)
        self.assertEqual(before,self.catalog.read_bytes())
    def test_workbench_bundle_records_only_the_exact_subject(self):
        c,s=load_catalog(self.catalog);bundle=self.root/'reviews.json';subject='face:sit:eyes%3Dopen:mouth%3DX'
        write_json(bundle,{'version':2,'character':'example','reviews':[{'subject':subject,'signature':character_reviews(c,s)[subject]['signature'],'decision':'approved','reviewer':'Fixture','notes':'One face case inspected.','proof':'data:image/png;base64,'+base64.b64encode((self.root/'body.png').read_bytes()).decode()}]})
        apply_review_bundle(self.catalog,bundle);states=check_reviews(self.catalog);self.assertEqual(states[subject],'approved');self.assertEqual(states['pose:sit'],'unreviewed')
    def test_registration_patch_is_revision_checked_and_stales_pose(self):
        self.approve();_,s=load_catalog(self.catalog);after=read_json(self.catalog.parent/'character.json')['poses']['sit'];after['anchors']['neck']=[8,9]
        patch={'version':1,'character':'example','base_signature':signature(s),'changes':[{'pose':'sit','before':s['poses']['sit'],'after':after}]};write_json(self.root/'patch.json',patch)
        apply_registration(self.catalog,self.root/'patch.json');self.assertEqual(check_reviews(self.catalog)['pose:sit'],'stale')
        with self.assertRaisesRegex(ValueError,'different source'):apply_registration(self.catalog,self.root/'patch.json')
    def test_incoming_import_has_a_diff_and_never_overwrites_silently(self):
        before=(self.catalog.parent/'character.json').read_bytes();self.spec['origin']=[3,4];write_json(self.root/'character.json',self.spec)
        proposal=prepare_import(self.catalog,self.root/'character.json',self.root/'proposal')
        self.assertEqual(before,(self.catalog.parent/'character.json').read_bytes());self.assertIn('origin',read_json(proposal)['fields'])
        original=read_json(proposal);changed=read_json(proposal);changed['fields']={};write_json(proposal,changed)
        with self.assertRaisesRegex(ValueError,'diff does not match'):apply_import(self.catalog,proposal)
        self.assertEqual(before,(self.catalog.parent/'character.json').read_bytes());write_json(proposal,original)
        apply_import(self.catalog,proposal);self.assertEqual(read_json(self.catalog.parent/'character.json')['origin'],[3,4])
        with self.assertRaisesRegex(ValueError,'stale'):apply_import(self.catalog,proposal)

if __name__=='__main__':unittest.main()
