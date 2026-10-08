import unittest
from datetime import datetime

from generator import coupons as cp
from generator import news
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


class NewsTest(unittest.TestCase):
    def test_signals_need_team_and_keyword_in_same_sentence(self):
        items = [news.norm("Arsenal striker ruled out for three weeks. Chelsea win again"),
                 news.norm("Chelsea name new head coach after Sunday defeat")]
        arsenal = news.headline_signals(items, news.team_aliases(["Arsenal FC", "Arsenal"]))
        chelsea = news.headline_signals(items, news.team_aliases(["Chelsea FC", "Chelsea"]))
        self.assertEqual(arsenal["absence"], 1)
        self.assertEqual(chelsea["absence"], 0)
        self.assertEqual(chelsea["coach"], 1)

    def test_polish_keywords_without_diacritics(self):
        items = [news.norm("Kontuzja lidera! Legia Warszawa bez kapitana w niedzielę")]
        s = news.headline_signals(items, news.team_aliases(["Legia Warszawa"]))
        self.assertEqual(s["absence"], 1)

    def test_injuries_lower_expected_goals(self):
        ah, dh, aa, da, adjusted = news.adjustments({"home": {"out": ["A", "B", "C"], "doubtful": []}})
        self.assertTrue(adjusted)
        self.assertLess(ah, 1)
        self.assertGreater(dh, 1)
        self.assertEqual((aa, da), (1, 1))
        self.assertGreaterEqual(news.adjustments({"home": {"out": list("ABCDEFGHIJKLMNOPQRST")}})[0], 1 - news.CAP)

    def test_no_news_no_adjustment(self):
        self.assertFalse(news.adjustments(None)[-1])


class ResearchTest(unittest.TestCase):
    def test_key_striker_out_lowers_attack(self):
        from generator import research
        team = {"absences": [{"player": "X", "position": "FWD", "importance": "key", "status": "out"}],
                "motivation": 0, "rotation_risk": 0, "new_coach": False}
        att, dfn, flags = research.team_factors(team, 1.0)
        self.assertAlmostEqual(att, 0.93)
        self.assertEqual(dfn, 1.0)
        self.assertEqual(flags, ["absence"])

    def test_research_call_parses_structured_output(self):
        import json
        from types import SimpleNamespace as NS
        from generator import research
        payload = {"matches": [{"id": 7, "confidence": 0.9,
                                "home": {"absences": [], "probable_lineup": [], "motivation": 2, "rotation_risk": 0, "new_coach": False},
                                "away": {"absences": [], "probable_lineup": [], "motivation": 0, "rotation_risk": 2, "new_coach": True}}]}
        calls = []

        def create(**kw):
            calls.append(kw)
            text = json.dumps(payload) if "format" in kw.get("output_config", {}) else "notes"
            return NS(content=[NS(type="text", text=text)], stop_reason="end_turn",
                      usage=NS(server_tool_use=NS(web_search_requests=2)))

        client = NS(messages=NS(create=create))
        match = {"id": 7, "home": "A", "away": "B", "home_id": 1, "away_id": 2, "utc": "2026-10-10T18:00:00Z"}
        found, searches = research._research_league(client, research.DEFAULTS, "League", [match], {}, print)
        self.assertEqual(searches, 2)
        self.assertEqual(found[7]["home"]["motivation"], 2)
        self.assertEqual(calls[0]["model"], "claude-haiku-5-5")
        self.assertEqual(calls[0]["tools"][0]["type"], "web_search_20250305")


class OddsTest(unittest.TestCase):
    def test_value_and_allowed_bookmaker(self):
        from generator import odds
        snap = {"avg": {"1": 2.0, "X": 3.4, "2": 3.8},
                "books": {"a": {"title": "A", "1": 2.2, "X": 3.3, "2": 3.6}, "b": {"title": "B", "1": 2.1, "X": 3.5, "2": 3.9}}}
        rows = odds.view({"opening": snap, "current": snap}, {"1": 0.5, "X": 0.25, "2": 0.25},
                         {"bookmakers": {"b": {"name": "Bookie B", "url": "https://example.com/aff"}}})
        home = rows[0]
        self.assertEqual((home["best"], home["book"]), (2.1, "b"))  # "a" nie jest na liście - pomijamy
        self.assertTrue(home["is_value"])
        self.assertFalse(rows[1]["is_value"])


class TranslationsTest(unittest.TestCase):
    def test_all_languages_have_same_keys_and_placeholders(self):
        import json, os, re
        d = os.path.join(os.path.dirname(os.path.dirname(__file__)), "i18n")
        en = json.load(open(os.path.join(d, "en.json"), encoding="utf-8"))
        ph = lambda v: sorted(re.findall(r"{\w+}", json.dumps(v, ensure_ascii=False)))
        for name in os.listdir(d):
            data = json.load(open(os.path.join(d, name), encoding="utf-8"))
            for section in ("meta", "ui", "markets", "analysis"):
                self.assertEqual(set(data[section]), set(en[section]), f"{name}:{section}")
                for key, value in en[section].items():
                    if section != "meta":
                        self.assertEqual(ph(data[section][key]), ph(value), f"{name}:{section}.{key}")


if __name__ == "__main__":
    unittest.main()
