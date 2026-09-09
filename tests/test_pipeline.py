import copy
import array
import math
import tempfile
import unittest
import wave
import zipfile
from unittest.mock import patch
from pathlib import Path

from PIL import ImageChops

from klassic.project import import_transcript, load_episode, make_shots, read_json, validate_cues, write_json
from klassic.render import Compositor, mouth_shape, srt_time, subtitle_chunks
from klassic.reference import build_reference
from klassic.motion import CelTransitions, MouthTrack, close_pauses
from klassic.audio import detect_pauses, RATE
from klassic.guest import mouth_layers
from PIL import Image, ImageOps
from klassic.cels import load_transition_library

ROOT = Path(__file__).resolve().parents[1]


class InputTests(unittest.TestCase):
    def test_multiline_transcript_preserves_words_and_speaker_changes(self):
        turns = import_transcript("BUCKLEY: A question?\nJENKINS: First sentence.\nSecond sentence.\nBUCKLEY: Next?", "Buckley", "Jenkins")
        self.assertEqual([t["speaker"] for t in turns], ["host", "guest", "host"])
        self.assertEqual(turns[1]["text"], "First sentence. Second sentence.")

    def test_moderator_is_not_silently_assigned_to_guest(self):
        with self.assertRaisesRegex(ValueError, "unknown speaker"):
            import_transcript("BUCKLEY: Hello.\nMODERATOR: Time.", "BUCKLEY", "JENKINS")

    def test_missing_labels_empty_input_and_empty_turn_fail(self):
        for text in ("", "An unlabeled introduction", "A:"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                import_transcript(text, "A", "B")

    def test_duplicate_ids_negative_pause_and_unknown_fields_fail(self):
        episode = load_episode(ROOT/"episodes/pilot/episode.json")
        mutations = [lambda e: e["turns"][1].update(id="t001"),
                     lambda e: e["turns"][0].update(pause_after=-1),
                     lambda e: e["turns"][0].update(pasue_after=1),
                     lambda e: e["turns"][0].update(id="../../escape")]
        with tempfile.TemporaryDirectory() as temp:
            for mutate in mutations:
                data = copy.deepcopy(episode)
                mutate(data)
                path = Path(temp)/"episode.json"
                write_json(path, data)
                with self.assertRaises(ValueError):
                    load_episode(path)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"bad.json"
            path.write_text('{"value": NaN}')
            with self.assertRaises(ValueError):
                read_json(path)


class TimingTests(unittest.TestCase):
    def test_audio_pauses_override_open_cues_but_preserve_short_gaps(self):
        # Quiet noise at each edge, a short consonant gap, and a long mid-phrase pause.
        parts = [(0.15, 50), (.2, 2000), (.06, 0), (.2, -2000), (.3, 50), (.2, 2000), (.15, 0)]
        samples = array.array("h", [v for seconds, v in parts for _ in range(round(seconds*RATE))])
        import sys
        if sys.byteorder != "little":
            samples.byteswap()
        pauses = detect_pauses(samples.tobytes())
        self.assertEqual(pauses, [{"start": 0, "end": .15}, {"start": .61, "end": .91}, {"start": 1.11, "end": 1.26}])
        cues = close_pauses([{"start": 0, "end": 1.26, "value": "B"}], pauses, 1.26)
        self.assertEqual([c["value"] for c in cues], ["X", "B", "X", "B", "X"])
        track = MouthTrack([{"speaker": "host", "start": 0, "cues": cues}], "host", 1.26)
        for pause in pauses:
            for frame in range(math.ceil(pause["start"]*240), math.ceil(pause["end"]*240)):
                self.assertEqual(track.sample(frame/240, .09), ("X", "X", 0))
        self.assertEqual(track.sample(.38, .09), ("B", "B", 0))

    def test_opening_transition_starts_after_rest_and_works_for_short_speech(self):
        cues = [{"start": 0, "end": .5, "value": "X"},
                {"start": .5, "end": .6, "value": "D"},
                {"start": .6, "end": 1, "value": "X"}]
        track = MouthTrack([{"speaker": "host", "start": 0, "cues": cues}], "host", 1)
        self.assertEqual(track.sample(.499, .09), ("X", "X", 0))
        self.assertEqual(track.sample(.5, .09), ("X", "D", 0))
        self.assertEqual(track.sample(.525, .09)[:2], ("X", "D"))
        self.assertEqual(track.sample(.575, .09)[:2], ("D", "X"))
        self.assertEqual(track.sample(.6, .09), ("X", "X", 0))

    def test_entirely_quiet_and_no_quiet_takes(self):
        self.assertEqual(detect_pauses(b"\0\0"*RATE), [{"start": 0, "end": 1}])
        self.assertEqual(detect_pauses(b"\xff\x7f"*RATE), [])
        with self.assertRaises(ValueError):
            detect_pauses(b"")
        with self.assertRaises(ValueError):
            close_pauses([], [{"start": .8, "end": 1.1}], 1)

    def test_cel_changes_leave_the_rest_of_the_scene_registered(self):
        timeline = {"scratch": False, "turns": [{"start": 0, "end": 1, "speaker": "host", "text": "Test.", "cues": [{"start": 0, "end": 1, "value": "A"}]}],
                    "shots": [{"start": 0, "end": 1, "camera": "wide"}]}
        comp = Compositor(timeline, ROOT/"assets/rig.json", 1448)
        closed = comp.frame(.5)
        timeline["turns"][0]["cues"][0]["value"] = "D"
        opened = Compositor(timeline, ROOT/"assets/rig.json", 1448).frame(.5)
        changed = ImageChops.difference(closed, opened).getbbox()
        self.assertIsNotNone(changed)
        x, y = comp.cels["host"][0]
        w, h = comp.cels["host"][1]["D"].size
        self.assertGreaterEqual(changed[0], x-3)
        self.assertGreaterEqual(changed[1], y-3)
        self.assertLessEqual(changed[2], x+w+3)
        self.assertLessEqual(changed[3], y+h+3)
        r, g, b = opened.split()
        self.assertEqual(r.tobytes(), g.tobytes())
        self.assertEqual(g.tobytes(), b.tobytes())

    def test_nose_is_above_every_cel_and_tween(self):
        timeline = {"scratch": False, "turns": [{"start": 0, "end": 1, "speaker": "host", "text": "Test.", "cues": [{"start": 0, "end": .5, "value": "D"}, {"start": .5, "end": 1, "value": "F"}]}],
                    "shots": [{"start": 0, "end": 1, "camera": "wide"}]}
        comp = Compositor(timeline, ROOT/"assets/rig.json", 1448)
        nose_core = (385, 288, 415, 310)
        expected = comp.scene.crop(nose_core).tobytes()
        for at in (.1, .43, .45, .48, .5, .7):
            self.assertEqual(comp.frame(at).convert("L").crop(nose_core).tobytes(), expected)

    def test_tween_arrives_at_closure_and_holds_it(self):
        turns = [{"speaker": "host", "start": 0, "end": 1,
                  "cues": [{"start": 0, "end": .4, "value": "D"},
                           {"start": .4, "end": .5, "value": "A"},
                           {"start": .5, "end": 1, "value": "C"}]}]
        track = MouthTrack(turns, "host", 1.5)
        source, target, mix = track.sample(.375, .09)
        self.assertEqual((source, target), ("D", "A"))
        self.assertTrue(0 < mix < 1)
        self.assertEqual(track.sample(.4, .09), ("A", "A", 0))
        self.assertEqual(track.sample(.44, .09), ("A", "A", 0))
        self.assertEqual(track.sample(1.1, .09), ("X", "X", 0))

    def test_tween_frame_is_intermediate_and_keeps_alpha(self):
        timeline = {"scratch": False, "turns": [{"start": 0, "end": 1, "speaker": "host", "text": "Test.", "cues": [{"start": 0, "end": 1, "value": "D"}]}],
                    "shots": [{"start": 0, "end": 1, "camera": "wide"}]}
        comp = Compositor(timeline, ROOT/"assets/rig.json", 320)
        tween = comp.transitions["host"][1]
        midpoint = tween.frame("B", "D", .5)
        self.assertEqual(midpoint.mode, "RGBA")
        self.assertEqual(midpoint.getpixel((0, 0))[3], 0)
        self.assertNotEqual(midpoint.tobytes(), tween.cells["B"].tobytes())
        self.assertNotEqual(midpoint.tobytes(), tween.cells["D"].tobytes())

    def test_all_transition_directions_use_exact_saved_drawings(self):
        timeline = {"scratch":False, "turns":[], "shots":[]}
        bank = Compositor(timeline,ROOT/"assets/rig.json",320).transitions["host"][1]
        self.assertEqual(len(bank.pairs),36)
        for pair, drawings in bank.pairs.items():
            a,b = pair
            self.assertIs(bank.frame(a,b,0),bank.cells[a])
            self.assertIs(bank.frame(a,b,1),bank.cells[b])
            self.assertIs(bank.frame(a,b,.25),drawings[0])
            self.assertIs(bank.frame(a,b,.75),drawings[1])
            self.assertIs(bank.frame(b,a,.25),drawings[1])
            self.assertIs(bank.frame(b,a,.75),drawings[0])
        incomplete = dict(bank.pairs)
        del incomplete["BF"]
        with self.assertRaisesRegex(ValueError,"all 36 pairs"):
            CelTransitions(bank.cells,incomplete)

    def test_transition_library_rejects_stale_endpoints_and_damaged_cels(self):
        original = ROOT/"assets/mouths/transitions/cels/library.json"
        data = read_json(original)
        endpoints = {s:ROOT/f"assets/mouths/host/{s}.png" for s in "ABCDEFGHX"}
        damaged = copy.deepcopy(data)
        damaged["endpoint_sha256"]["B"] = "changed"
        with patch("klassic.cels.read_json",return_value=damaged):
            with self.assertRaisesRegex(ValueError,"endpoint B changed"):
                load_transition_library(original,endpoints,(160,139))
        damaged = copy.deepcopy(data)
        damaged["cel_sha256"]["BC-1.png"] = "changed"
        with patch("klassic.cels.read_json",return_value=damaged):
            with self.assertRaisesRegex(ValueError,"BC-1.png changed"):
                load_transition_library(original,endpoints,(160,139))

    def test_nose_occlusion_survives_all_81_drawings(self):
        comp = Compositor({"scratch":False,"turns":[],"shots":[]},ROOT/"assets/rig.json",320)
        bank = comp.transitions["host"][1]
        drawings = list(bank.cells.values())+[f for frames in bank.pairs.values() for f in frames]
        nose_core = (385,288,415,310)
        expected = comp.scene.crop(nose_core).tobytes()
        for cel in drawings:
            frame = comp.scene.copy()
            comp.paint_cel(frame,"host",cel)
            self.assertEqual(frame.crop(nose_core).tobytes(),expected)

    def test_incomplete_character_cels_fail_instead_of_using_placeholder(self):
        rig = read_json(ROOT/"assets/rig.json")
        del rig["mouths"]["host"]["cels"]["D"]
        with patch("klassic.render.read_json", return_value=rig):
            with self.assertRaisesRegex(ValueError, "every Rhubarb shape"):
                Compositor({"shots": []}, ROOT/"assets/rig.json", 320)

    def test_mouth_closes_in_pause_and_changes_at_boundary(self):
        turn = {"start": 2, "end": 3, "cues": [{"start": 0, "end": .5, "value": "D"}, {"start": .5, "end": 1, "value": "A"}]}
        self.assertEqual(mouth_shape(turn, 2.49), "D")
        self.assertEqual(mouth_shape(turn, 2.5), "A")
        self.assertEqual(mouth_shape(turn, 3.01), "X")

    def test_overlapping_out_of_range_and_unknown_cues_fail(self):
        for cues in ([{"start": 0, "end": 2, "value": "A"}],
                     [{"start": 0, "end": 1, "value": "Q"}],
                     [{"start": 0, "end": .7, "value": "A"}, {"start": .6, "end": 1, "value": "B"}]):
            with self.assertRaises(ValueError):
                validate_cues(cues, 1)

    def test_shots_cover_pauses_and_sip_is_a_listening_cut(self):
        turns = [{"speaker": "host", "start": 0, "end": 2, "pause_after": .5},
                 {"speaker": "guest", "start": 2.5, "end": 14.5, "pause_after": .5}]
        shots = make_shots(turns, 15)
        self.assertEqual(shots[0]["start"], 0)
        self.assertEqual(shots[-1]["end"], 15)
        for left, right in zip(shots, shots[1:]):
            self.assertEqual(left["end"], right["start"])
        sip = next(s for s in shots if s.get("pose") == "host_sip")
        self.assertEqual(sip["camera"], "host")
        self.assertTrue(turns[1]["start"] <= sip["start"] < sip["end"] <= turns[1]["end"])

    def test_short_replies_stay_in_one_shot(self):
        self.assertEqual(len(make_shots([{"speaker": "guest", "start": 0, "end": .4, "pause_after": .6}], 1)), 1)

    def test_caption_clock_carries_milliseconds(self):
        self.assertEqual(srt_time(59.9998), "00:01:00,000")
        self.assertEqual(srt_time(3600), "01:00:00,000")

    def test_captions_stay_in_measured_take(self):
        turn = {"start": 1.2, "end": 8.4, "text": "An unusually detailed answer about the institutional structure of organized labor. "*3}
        chunks = subtitle_chunks(turn)
        self.assertEqual(chunks[0]["start"], turn["start"])
        self.assertAlmostEqual(chunks[-1]["end"], turn["end"])
        self.assertEqual(" ".join(c["text"].replace("\n", " ") for c in chunks), turn["text"].strip())

    def test_composited_frame_is_grayscale_and_sipping_speaker_fails(self):
        timeline = {"scratch": True, "turns": [{"start": 0, "end": 1, "speaker": "guest", "text": "Test.", "cues": [{"start": 0, "end": 1, "value": "D"}]}],
                    "shots": [{"start": 0, "end": 1, "camera": "host", "pose": "host_sip"}]}
        frame = Compositor(timeline, ROOT/"assets/rig.json", 320).frame(.5)
        self.assertEqual(frame.size, (320,240))
        r,g,b = frame.split()
        self.assertEqual(r.tobytes(), g.tobytes())
        self.assertEqual(g.tobytes(), b.tobytes())
        timeline["turns"][0]["speaker"] = "host"
        with self.assertRaisesRegex(ValueError, "active speaker"):
            Compositor(timeline, ROOT/"assets/rig.json", 320)


class ReferenceTests(unittest.TestCase):
    def test_selected_zip_clips_keep_order_and_record_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/"source.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                wav.writeframes(array.array("h", [1000,-1000]*24000).tobytes())
            archive = root/"pack.zip"
            with zipfile.ZipFile(archive,"w") as pack:
                pack.write(source,"B.wav")
                pack.write(source,"A.wav")
            output = root/"reference.wav"
            build_reference(archive,["A.wav","B.wav"],output,"https://example.com/source")
            metadata = read_json(output.with_suffix(".source.json"))
            self.assertEqual([c["member"] for c in metadata["clips"]],["A.wav","B.wav"])
            self.assertAlmostEqual(metadata["duration"],4.18)
            with wave.open(str(output),"rb") as wav:
                samples = array.array("h",wav.readframes(wav.getnframes()))
                self.assertEqual(wav.getframerate(),24000)
            self.assertEqual(set(samples[48000:52320]),{0})
            self.assertLessEqual(max(map(abs,samples)),23200)

    def test_missing_clip_leaves_no_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary)/"empty.zip"
            with zipfile.ZipFile(archive,"w"):
                pass
            output = Path(temporary)/"reference.wav"
            with self.assertRaisesRegex(ValueError,"Missing"):
                build_reference(archive,["missing.wav"],output,"https://example.com/source")
            self.assertFalse(output.exists())


class GuestMouthTests(unittest.TestCase):
    outline = read_json(ROOT/"assets/characters/fromm/portrait.json")["front_outline"]

    def test_open_mouths_keep_inside_lip_and_upper_lip_bridge(self):
        # Actual ink points on the C/H inner lip and C/D upper-lip underside.
        # Earlier masks erased the recess or broke the horizontal connection.
        for shape, points in {"C": [(182, 270), (75, 220)],
                              "H": [(189, 270), (174, 300)], "D": [(70, 200)]}.items():
            cel = Image.open(ROOT/f"assets/mouths/host/{shape}.png")
            reference = ImageOps.mirror(cel)
            _, ink = mouth_layers(cel, 205, self.outline)
            for point in points:
                with self.subTest(shape=shape, point=point):
                    self.assertLess(reference.getpixel(point)[0], 60)
                    self.assertGreater(ink.getpixel(point)[3], 240)
                    self.assertLess(ink.getpixel(point)[0], 80)

    def test_back_outline_is_removed_without_removing_skin_coverage(self):
        cel = Image.open(ROOT/"assets/mouths/host/X.png")
        coverage, ink = mouth_layers(cel, 205, self.outline)
        reference = ImageOps.mirror(cel)
        point = next((x, 230) for x in range(360, 418)
                     if reference.getpixel((x, 230))[0] < 60 and reference.getpixel((x, 230))[3] > 240)
        self.assertGreater(coverage.getpixel(point), 240)
        self.assertLess(ink.getpixel(point)[3], 10)

    def test_outline_oval_excludes_rounded_chin_top_and_back(self):
        # Regions on actual source drawings, clear of lip rims and mouth ink.
        chins = {"X": (115, 280, 230, 345), "A": (115, 280, 230, 345),
                 "G": (130, 280, 225, 345), "E": (145, 345, 240, 385),
                 "F": (130, 335, 245, 380), "D": (210, 360, 280, 400),
                 "C": (210, 350, 280, 399), "H": (185, 330, 285, 380)}
        for shape, chin in chins.items():
            cel = Image.open(ROOT/f"assets/mouths/host/{shape}.png")
            reference = ImageOps.mirror(cel)
            _, ink = mouth_layers(cel, 205, self.outline)
            for region in (chin, (180, 80, 300, 160), (350, 180, 400, 340)):
                checked = 0
                for y in range(region[1], region[3]):
                    for x in range(region[0], region[2]):
                        color = reference.getpixel((x, y))
                        if color[0] < 60 and color[3] > 240:
                            checked += 1
                            self.assertLess(ink.getpixel((x, y))[3], 20, (shape, x, y))
                self.assertGreater(checked, 0, (shape, region))


if __name__ == "__main__":
    unittest.main()
