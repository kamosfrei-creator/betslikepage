import unittest
from datetime import datetime

from generator import coupons as cp
from generator.model import LeagueModel, markets, score_matrix


class ModelTest(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        p = markets(score_matrix(1.6, 1.1))
        self.assertAlmostEqual(p["1"] + p["X"] + p["2"], 1.0, places=6)
        self.assertAlmostEqual(p["O25"] + p["U25"], 1.0, places=6)

    def test_stronger_team_is_favourite(self):
        finished = []
        for i in range(10):
            finished.append({"utc": f"2026-09-{i + 1:02d}T18:00:00Z", "home_id": "A", "away_id": "B",
                             "home_goals": 3, "away_goals": 0})
            finished.append({"utc": f"2026-09-{i + 1:02d}T20:00:00Z", "home_id": "B", "away_id": "A",
                             "home_goals": 0, "away_goals": 2})
        model = LeagueModel(finished, datetime(2026, 10, 1))
        probs = model.predict("A", "B")["probs"]
        self.assertGreater(probs["1"], 0.6)
        self.assertEqual(model.team_info("A")["form"], "WWWWW")


class CouponTest(unittest.TestCase):
    def test_settle(self):
        self.assertTrue(cp.settle("1X", 1, 1))
        self.assertFalse(cp.settle("O25", 1, 1))
        self.assertTrue(cp.settle("BTTS", 2, 1))
        self.assertTrue(cp.settle("U35", 2, 1))

    def test_main_pick_avoids_near_certain_markets(self):
        p = markets(score_matrix(3.0, 0.3))
        self.assertLessEqual(cp.main_pick(p)["p"], cp.MAX_P)

    def test_coupon_one_leg_per_match(self):
        matches = [{"id": i, "prediction": {"probs": markets(score_matrix(1.5 + i / 10, 1.0))}} for i in range(6)]
        coupons = cp.build_coupons(matches)
        for c in coupons.values():
            ids = [leg["match"]["id"] for leg in c["legs"]]
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
