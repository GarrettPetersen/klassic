import math
import unittest

from klassic.accent import windows
from klassic.puppet import Channel, affine_inverse, arm_point, forward, inverse


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.character={'waist':[320,625], 'arms':{
            'free':{'shoulder':[155,402],'degrees':-24},
            'cigarette':{'shoulder':[419,412],'degrees':8}}}
        self.state={'lean':3,'free':1,'cigarette':.8}

    def test_feet_stay_fixed(self):
        for point in [(350,680),(510,740),(420,900)]:
            self.assertEqual(point,forward(point,self.character,self.state))

    def test_head_and_mouth_share_rigid_transform(self):
        eye,mouth=(360,266),(375,350)
        self.assertAlmostEqual(math.dist(eye,mouth), math.dist(
            forward(eye,self.character,self.state),forward(mouth,self.character,self.state)), places=8)

    def test_shoulders_stay_attached_and_complete_arms_do_not_stretch(self):
        for name,bone in self.character['arms'].items():
            elbow=bone['shoulder']; wrist=(elbow[0]+40,elbow[1]-65)
            moved_elbow=arm_point(elbow,self.character,self.state,name)
            self.assertLess(math.dist(moved_elbow,forward(elbow,self.character,self.state)),1e-8)
            self.assertAlmostEqual(math.dist(elbow,wrist),math.dist(moved_elbow,arm_point(wrist,self.character,self.state,name)),places=8)

    def test_inverse_mesh_and_arm_affine(self):
        for point in [(350,260),(350,570),(380,620),(400,649)]:
            moved=forward(point,self.character,self.state)
            self.assertLess(math.dist(point,inverse(moved,self.character,self.state)),.02)
        mapping=lambda p:arm_point(p,self.character,self.state,'free')
        a,b,c,d,e,f=affine_inverse(mapping)
        self.assertGreater(a*e-b*d,0, 'Arm transform must never mirror handedness')
        p=mapping((250,615))
        self.assertLess(math.dist((250,615),(a*p[0]+b*p[1]+c,d*p[0]+e*p[1]+f)),1e-7)

    def test_channels_hold_and_ease(self):
        c=Channel([[0,0],[1,0],[2,1],[3,1]],3)
        self.assertEqual(c.sample(.5),0)
        self.assertEqual(c.sample(2.5),1)
        self.assertAlmostEqual(c.sample(1.5),.5)
        with self.assertRaises(ValueError):c.sample(-1)
        with self.assertRaises(ValueError):Channel([[0,0],[1,1],[1,0],[3,0]],3)


class AccentWindowTests(unittest.TestCase):
    def test_short_clips_are_not_padded_into_fake_evidence(self):
        self.assertEqual(windows(2.9),[])
        self.assertEqual(windows(3),[(0,3)])

    def test_last_window_reaches_the_tail_without_tiny_fragments(self):
        self.assertEqual(windows(10),[(0,6),(3,9),(4,10)])
        self.assertEqual(windows(12),[(0,6),(3,9),(6,12)])
        for invalid in (0,-1,float('nan')):
            with self.assertRaises(ValueError):windows(invalid)


if __name__=='__main__':unittest.main()
