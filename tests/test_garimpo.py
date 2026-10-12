import os, sys, unittest
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import garimpo as g  # noqa: E402


def repo(name, stars, created="2026-01-01", pushed="2026-06-01", desc="a tool"):
    return {"full_name": name, "html_url": "https://github.com/" + name, "description": desc, "stargazers_count": stars,
            "language": "Python", "license": {"spdx_id": "MIT"}, "pushed_at": pushed + "T00:00:00Z", "created_at": created + "T00:00:00Z"}


class Garimpo(unittest.TestCase):
    def test_query_adds_filters(self):
        q = g.query_for("net worth tracker", today=date(2026, 6, 30))
        self.assertIn("net worth tracker in:name,description,topics", q)
        self.assertIn("stars:60..60000", q)
        self.assertIn("pushed:>=2026-04-01", q)

    def test_new_query(self):
        self.assertEqual(g.query_for("@new 7", today=date(2026, 6, 30)), "created:>=2026-06-23 stars:>=60 archived:false")

    def test_link_lists_are_dropped(self):
        found = g.collect([("A", "x")], search_fn=lambda q: [repo("me/awesome-things", 900), repo("me/tool", 900)], pause=0, log=lambda *_: None)
        self.assertEqual(list(found), ["me/tool"])

    def test_failed_search_does_not_stop_the_run(self):
        def flaky(q):
            if q == "bad":
                raise OSError("network")
            return [repo("me/tool", 100)]
        found = g.collect([("A", "bad"), ("B", "ok")], search_fn=flaky, pause=0, log=lambda *_: None)
        self.assertEqual(found["me/tool"]["themes"], {"B"})

    def test_only_new_or_grown_come_back(self):
        seen = {}
        first = g.select({"a/a": {"r": repo("a/a", 1000), "themes": {"T"}}, "b/b": {"r": repo("b/b", 1000), "themes": {"T"}}}, seen, "2026-06-01")
        self.assertEqual({x["name"] for x in first}, {"a/a", "b/b"})
        second = g.select({"a/a": {"r": repo("a/a", 1050), "themes": {"T"}},      # +5%: stays out
                           "b/b": {"r": repo("b/b", 1200), "themes": {"T"}},      # +20%: comes back
                           "c/c": {"r": repo("c/c", 80), "themes": {"T"}}}, seen, "2026-06-08")
        self.assertEqual({x["name"] for x in second}, {"b/b", "c/c"})
        self.assertEqual(seen["a/a"]["stars"], [["2026-06-01", 1000], ["2026-06-08", 1050]])

    def test_young_and_climbing_beats_old_and_parked(self):
        now = datetime(2026, 6, 30)
        young = g.score(repo("y/y", 3000, created="2026-06-01", pushed="2026-06-29"), 0, now)
        old = g.score(repo("o/o", 9000, created="2019-01-01", pushed="2026-04-10"), 0, now)
        self.assertGreater(young, old)

    def test_each_repository_listed_once_and_capped(self):
        rows = [{"name": "r%d" % i, "themes": ["A", "B"], "score": 100 - i} for i in range(20)]
        groups = g.by_theme(rows)
        names = [x["name"] for v in groups.values() for x in v]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(groups["A"]), g.PER_THEME)
        self.assertEqual(len(groups["B"]), g.PER_THEME)


if __name__ == "__main__":
    unittest.main()
