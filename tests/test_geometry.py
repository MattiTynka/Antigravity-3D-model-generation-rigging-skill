# NEW: pure-math tests, deliberately independent from Blender.
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from geometry_math import normalized_weights, validate_bones, triangle_uv_area, surface_fingerprint, gaussian_falloff, parabolic_arc_weight

class GeometryTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(normalized_weights([('a',0.2),('b',0.8)],4), [('b',0.8),('a',0.2)])
        out=normalized_weights([('a',0.2),('b',0.5),('c',0.3)],2)
        self.assertAlmostEqual(sum(w for _,w in out),1)
        self.assertEqual(len(out),2)
        with self.assertRaises(ValueError): normalized_weights([('a',float('nan'))],4)
        with self.assertRaises(ValueError): normalized_weights([('a',-1)],4)
    def test_skeleton_cycles_and_zero_length(self):
        bone=lambda n,p,h,t: dict(name=n,parent=p,head=h,tail=t)
        with self.assertRaises(ValueError): validate_bones([bone('a',None,[0,0,0],[0,0,0])])
        with self.assertRaises(ValueError): validate_bones([bone('a','b',[0,0,0],[0,0,1]),bone('b','a',[0,0,1],[0,0,2])])
        self.assertEqual([x['name'] for x in validate_bones([bone('b','a',[0,0,1],[0,0,2]),bone('a',None,[0,0,0],[0,0,1])])],['a','b'])
    def test_uv_area(self):
        self.assertEqual(triangle_uv_area([(0,0),(1,0),(0,1)]),0.5)
        self.assertEqual(triangle_uv_area([(0,0),(1,0),(2,0)]),0)
    def test_fingerprint_order_invariant_but_uv_sensitive(self):
        tri=[(0,0,0,0,0),(1,0,0,1,0),(0,1,0,0,1)]
        self.assertEqual(surface_fingerprint([tri]),surface_fingerprint([tri[1:]+tri[:1]]))
        changed=[*tri]; changed[0]=(0,0,0,.2,0)
        self.assertNotEqual(surface_fingerprint([tri]),surface_fingerprint([changed]))
        self.assertNotEqual(surface_fingerprint([tri]),surface_fingerprint([list(reversed(tri))]))
    def test_facial_math(self):
        self.assertAlmostEqual(gaussian_falloff(0.0, 0.1), 1.0)
        self.assertAlmostEqual(gaussian_falloff(0.1, 0.1), 0.6065306597126334)
        self.assertAlmostEqual(gaussian_falloff(0.3, 0.1), 0.011108996538242306)
        with self.assertRaises(ValueError): gaussian_falloff(0.1, -1.0)
        self.assertAlmostEqual(parabolic_arc_weight(0.0, 0.065), 0.0)
        self.assertAlmostEqual(parabolic_arc_weight(0.065, 0.065), 1.0)
        self.assertAlmostEqual(parabolic_arc_weight(-0.065, 0.065), 1.0)
        self.assertTrue(0.0 < parabolic_arc_weight(0.0325, 0.065) < 1.0)
        with self.assertRaises(ValueError): parabolic_arc_weight(0.0, 0.0)
if __name__=='__main__': unittest.main()

