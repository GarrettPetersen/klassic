import copy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from klassic.cels import remove_green_matte
from klassic.gestures import ArmLibrary,GestureTrack


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.event={'start':2,'end':5,'keys':[
            [0,'relaxed',0],[.5,'turn',.5],[1,'up',1],[2,'up',1],[3,'relaxed',0]]}
        self.poses={'relaxed','turn','up'}

    def test_a_gesture_holds_its_drawing_and_returns_to_rest(self):
        track=GestureTrack([self.event],8,self.poses)
        self.assertEqual(track.sample(1),('relaxed',0))
        self.assertEqual(track.sample(3.2),('up',1))
        self.assertEqual(track.sample(3.8),('up',1))
        self.assertEqual(track.sample(7),('relaxed',0))

    def test_only_joint_motion_interpolates_between_drawing_changes(self):
        track=GestureTrack([self.event],8,self.poses)
        self.assertEqual(track.sample(2.75),('turn',.75))
        self.assertEqual(track.sample(3),('up',1))

    def test_invalid_pose_and_overlapping_events_fail(self):
        for keys in ([],[[0,'relaxed',0]],[[0,'missing',0],[3,'relaxed',0]],
                     [[0,'relaxed',0],[3,'up',1]],[[0,'up',1],[3,'relaxed',0]]):
            bad=copy.deepcopy(self.event);bad['keys']=keys
            with self.assertRaises(ValueError):GestureTrack([bad],8,self.poses)
        with self.assertRaises(ValueError):GestureTrack([self.event,self.event],8,self.poses)

    def test_green_key_preserves_partially_covered_black_outlines(self):
        image=Image.new('RGB',(3,1))
        image.putdata([(0,255,0),(0,128,0),(220,220,220)])
        result=remove_green_matte(image)
        self.assertEqual(result.getpixel((0,0))[3],0)
        edge=result.getpixel((1,0))
        self.assertEqual(edge[:3],(0,0,0))
        self.assertTrue(100<edge[3]<150)
        self.assertEqual(result.getpixel((2,0)),(220,220,220,255))

    def test_measured_key_removes_dim_green_without_clipping_black_edges(self):
        image=Image.new('RGB',(2,1));image.putdata([(0,224,0),(0,112,0)])
        result=remove_green_matte(image,background_green=224)
        self.assertEqual(result.getpixel((0,0))[3],0)
        self.assertEqual(result.getpixel((1,0)),(0,0,0,128))


class ArmLibraryTests(unittest.TestCase):
    def test_cloth_grading_preserves_ink_skin_and_alpha(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cel=Image.new('RGBA',(5,1))
            pixels=[(12,12,12,255),(34,34,34,255),(220,220,220,255),
                    (255,255,255,128),(0,0,0,0)]
            cel.putdata(pixels);cel.save(root/'rest.png')
            curve=[v if v<=12 or v>=64 else round(12+(v-12)*13/22) if v<=34 else round(25+(v-34)*39/30) for v in range(256)]
            spec={'version':2,'gray_curve':curve,'canvas':[5,1],'anatomical_hand':'right',
                  'poses':{'relaxed':{'file':'rest.png','anchor':[1,0],'anatomical_hand':'right','digits':4}}}
            path=root/'library.json';path.write_text(json.dumps(spec))
            result=ArmLibrary(path).cels['relaxed']
            self.assertEqual(result.getpixel((1,0)),(25,25,25,255))
            for x in (0,2,3,4):self.assertEqual(result.getpixel((x,0)),pixels[x])
            spec['gray_curve'][100]=-1;path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):ArmLibrary(path)

    def test_a_pose_cannot_change_the_arm_hand_or_digit_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cel=Image.new('RGBA',(24,24))
            cel.paste((30,30,30,255),(4,4,20,20));cel.save(root/'rest.png')
            pose={'file':'rest.png','anchor':[12,6],'anatomical_hand':'right','digits':4}
            spec={'version':2,'gray_curve':list(range(256)),'canvas':[24,24],'anatomical_hand':'right','poses':{'relaxed':pose}}
            path=root/'library.json';path.write_text(json.dumps(spec))
            self.assertEqual(ArmLibrary(path).spec['anatomical_hand'],'right')
            for changes in ({'anatomical_hand':'left'},{'digits':5}):
                invalid=copy.deepcopy(spec);invalid['poses']['relaxed'].update(changes)
                path.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):ArmLibrary(path)


if __name__=='__main__':unittest.main()
