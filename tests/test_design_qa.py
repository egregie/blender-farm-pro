"""D-6's instrument has to be able to see a design failing.

`design_qa.py` is the one place the design channel is read from, and it had no
tests. The defect that made the case: agreement is area-weighted and a substrate
is 55-99.9% of these faces, so the headline figure moves very little whatever
happens to a field -- and the per-field IoU column, which is where a failure
would show, was being computed over a mask that dropped every dark field
*exactly where our render painted it correctly*.

The result was a report whose ranking was inverted. Ritalin held the group's
BEST agreement, 99.87%, with an IoU of 0.043 on its only field; Cialis, the
worst agreement in the group, had the third-best fields. Both figures were
honest arithmetic over the wrong set of pixels.

These are synthetic: the properties are about masks and index maps, and stating
them in pixels is clearer and faster than rendering a carton to demonstrate one.
"""
import unittest

import numpy as np

from scripts.design_qa import DARK_V, LUMA, _agreement, scored_mask


def _hex(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


class TestADarkFieldIsScoredWhereTheSpecExpectsOne(unittest.TestCase):
    """The dark cut keeps printed TYPE out of the figures, not dark FIELDS.

    Ritalin's `#2E1D3C` is its only field. Under the bare brightness cut its own
    pixels were dropped, so the field was scored only over the pixels our render
    got WRONG, and reported 0.043 against a render that places it correctly.
    """

    SUBSTRATE, FIELD = "#C0C0C0", "#2E1D3C"
    N, LO, HI, SHIFT = 100, 20, 80, 2

    def setUp(self):
        self.palette = np.stack([_hex(self.SUBSTRATE), _hex(self.FIELD)])
        # The spec draws one dark panel; our render places it two pixels off.
        self.spec = np.zeros((self.N, self.N), dtype=int)
        self.spec[self.LO:self.HI, self.LO:self.HI] = 1
        self.ours = np.zeros((self.N, self.N), dtype=int)
        self.ours[self.LO + self.SHIFT:self.HI + self.SHIFT,
                  self.LO + self.SHIFT:self.HI + self.SHIFT] = 1
        self.frame = self.palette[self.ours]

    def test_the_bare_brightness_cut_scores_only_our_mistakes(self):
        """The defect, stated so it cannot come back unnoticed."""
        bare = self.frame.max(-1) >= DARK_V
        self.assertFalse(bare[self.ours == 1].any(),
                         "the field our render painted is dropped entirely")
        self.assertEqual(_agreement(self.ours, self.spec, bare, 2)["iou"][1], 0.0,
                         "leaving the field scored over the misses alone")

    def test_the_field_is_scored_on_what_the_spec_expects_there(self):
        m = scored_mask(self.frame, self.palette, self.spec)
        self.assertTrue(m[self.spec == 1].all())
        side, shift = self.HI - self.LO, self.SHIFT
        self.assertAlmostEqual(_agreement(self.ours, self.spec, m, 2)["iou"][1],
                               round((side - shift) ** 2 / side ** 2, 3), places=3)

    def test_on_a_dark_field_the_figure_reads_as_recall(self):
        """What the cut still cannot answer, stated rather than left implied.

        A dark pixel where the spec draws the light substrate is either this
        field overrunning its outline or the printed type the spec does not
        carry, and no rule over colour alone separates them. The cut drops it,
        so a dark field's overspill costs nothing and its IoU degenerates to
        recall -- the figure catches a field placed short, not one placed wide.
        """
        m = scored_mask(self.frame, self.palette, self.spec)
        got, want = (self.ours == 1) & m, (self.spec == 1) & m
        self.assertEqual((got & ~want).sum(), 0, "no overspill survives the cut")
        self.assertAlmostEqual(_agreement(self.ours, self.spec, m, 2)["iou"][1],
                               round(float((got & want).sum() / want.sum()), 3),
                               places=3)

    def test_a_correctly_placed_dark_field_scores_one(self):
        frame = self.palette[self.spec]
        m = scored_mask(frame, self.palette, self.spec)
        self.assertEqual(_agreement(self.spec, self.spec, m, 2)["iou"][1], 1.0)

    def test_type_the_spec_does_not_carry_is_still_cut(self):
        """The reason the cut exists at all: our render prints type, the spec
        does not, and scoring it would measure the type grid."""
        frame = self.palette[self.spec].copy()
        frame[5:9, 5:40] = 0.02                      # a printed row on the board
        m = scored_mask(frame, self.palette, self.spec)
        self.assertFalse(m[5:9, 5:40].any())


class TestTheTwoDarknessTestsAgreeInTheDirectionThatMatters(unittest.TestCase):
    """The cut is on the pixel's MAX channel and the restore on the fill's LUMA.

    Different tests, deliberately -- but the asymmetry is only safe one way
    round. Luma is a weighted mean of the channels, so luma <= max always, and
    no fill the cut can reach is left unrestored. Reversing them would drop
    fields silently again, which is why this is asserted rather than assumed.
    """

    def test_every_fill_the_cut_reaches_is_restored(self):
        rng = np.random.default_rng(0)
        colours = np.concatenate([rng.random((4000, 3)), rng.random((4000, 3)) * 0.4])
        cut = colours.max(-1) < DARK_V
        self.assertTrue(cut.any(), "the sample must contain fills the cut reaches")
        self.assertTrue(((colours * LUMA).sum(1) < DARK_V)[cut].all())


if __name__ == "__main__":
    unittest.main()
