import copy
import unittest

from klassic.presentation import screen_time, title_at


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.timeline = {
            'presentation': {'title_after_turn': 'teaser'},
            'turns': [
                {'id': 'teaser', 'start': 0, 'end': 4.5, 'pause_after': .5},
                {'id': 'welcome', 'start': 5, 'end': 9, 'pause_after': 0},
            ],
        }

    def test_teaser_stays_at_zero_and_welcome_moves_past_title(self):
        cut = title_at(self.timeline)
        self.assertEqual(cut, 5)
        self.assertEqual(screen_time(0, cut, 6.25), 0)
        self.assertEqual(screen_time(4.5, cut, 6.25), 4.5)
        self.assertEqual(screen_time(5, cut, 6.25), 11.25)
        self.assertEqual(screen_time(5, cut, 6.25, end=True), 5)
        self.assertEqual(screen_time(9, cut, 6.25), 15.25)

    def test_opening_title_offsets_all_dialogue(self):
        del self.timeline['presentation']
        cut = title_at(self.timeline)
        self.assertEqual(cut, 0)
        self.assertEqual(screen_time(0, cut, 6.25), 6.25)

    def test_invalid_title_boundary_fails(self):
        for after in ('missing', 'welcome'):
            data = copy.deepcopy(self.timeline)
            data['presentation']['title_after_turn'] = after
            with self.assertRaises(ValueError):
                title_at(data)
        self.timeline['turns'][1]['start'] = 5.5
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            title_at(self.timeline)
