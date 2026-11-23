"""Unit tests (stdlib unittest; no pytest needed).

Run from the repo root:  python -m unittest discover -s python/tests -v

Expected values come from definitions or hand calculation, never from the
code under test (guideline section 09).
"""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze as A  # noqa: E402
import integrate as I  # noqa: E402
import workbook_replica as W  # noqa: E402


class TestMoments(unittest.TestCase):
    def test_hand_example(self):
        # r = [-2,-1,0,1,2]: mean 0, m2 = 2, m3 = 0, m4 = 34/5 = 6.8
        m = A.moments(np.array([-2, -1, 0, 1, 2, -2, 2, 0], float))
        # recompute by hand for this 8-point set: values -2,-1,0,1,2,-2,2,0
        x = np.array([-2, -1, 0, 1, 2, -2, 2, 0], float)
        m2 = np.mean(x**2); m4 = np.mean(x**4)
        self.assertAlmostEqual(m["skew"], 0.0, places=12)
        self.assertAlmostEqual(m["excess_kurtosis"], m4 / m2**2 - 3, places=12)
        self.assertAlmostEqual(m["sd"], math.sqrt(np.sum(x**2) / 7), places=12)

    def test_large_normal_sample_is_close_to_theory(self):
        rng = np.random.default_rng(1)
        m = A.moments(rng.normal(0, 0.01, 200_000))
        self.assertLess(abs(m["skew"]), 0.03)
        self.assertLess(abs(m["excess_kurtosis"]), 0.06)
        self.assertGreater(m["jb_p"], 0.001)

    def test_boundary_too_few_and_constant(self):
        with self.assertRaises(ValueError):
            A.moments(np.ones(5))
        with self.assertRaises(ValueError):
            A.moments(np.ones(20))  # zero variance


class TestIntervals(unittest.TestCase):
    def test_wilson_known_value(self):
        # 10 / 100, z = 1.96: textbook interval (0.0552, 0.1744)
        lo, hi = A.wilson(10, 100)
        self.assertAlmostEqual(lo, 0.0552, places=4)
        self.assertAlmostEqual(hi, 0.1744, places=4)

    def test_wilson_edges(self):
        # D-02 fix: floating point gives ~1e-17, not exactly 0 -> compare with tolerance
        self.assertAlmostEqual(A.wilson(0, 50)[0], 0.0, places=12)
        self.assertAlmostEqual(A.wilson(50, 50)[1], 1.0, places=12)
        self.assertTrue(all(math.isnan(v) for v in A.wilson(0, 0)))

    def test_exceedance_on_simulated_normal_matches_normal(self):
        """Statistical test: if data really are normal, the normal model must
        NOT be rejected (coverage check, fixed seed)."""
        rng = np.random.default_rng(20261123)
        x = rng.normal(0, 1, 60_000)
        tfit = A.fit_t(x[:40_000])
        rows = A.exceedance_table(x[:40_000], x[40_000:], [1, 2, 3], tfit)
        # D-03 fix: a fixed +/-15% ratio tolerance is too tight for k=3
        # (expected ~54 hits, SD of count ~7.3 -> 15% is only ~1.1 SD).
        # Correct criterion: the binomial test must not reject the true model.
        for r in rows:
            self.assertGreater(r["binom_p_vs_normal"], 0.01, r)
            self.assertLessEqual(r["ci95_low"], r["p_normal"])
            self.assertGreaterEqual(r["ci95_high"], r["p_normal"])
        self.assertGreater(tfit["df"], 30)  # near-normal data -> large df


class TestLjungBox(unittest.TestCase):
    def test_iid_not_rejected_and_garch_like_rejected(self):
        rng = np.random.default_rng(7)
        iid = rng.normal(size=3000)
        self.assertGreater(A.ljung_box_sq(iid)["p"], 0.01)
        vol = np.repeat(rng.choice([0.5, 3.0], 60), 50)  # regime-switching scale
        self.assertLess(A.ljung_box_sq(rng.normal(size=3000) * vol)["p"], 1e-6)


class TestIntegrate(unittest.TestCase):
    def test_duplicates_keep_last_and_drop_missing(self):
        # D-01 fix: the first version generated impossible dates (2024-02-30); use a real calendar
        days = pd.date_range("2024-01-03", periods=62).strftime("%Y-%m-%d").tolist()
        df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-02"] + days,
                           "close": [10, 11, 12] + [10.0] * 32 + [None] + [10.0] * 29})
        out, q = I.clean_prices(df)
        self.assertEqual(q["duplicate_dates"], 1)
        self.assertEqual(q["missing_close"], 1)
        self.assertEqual(out.loc[out["date"] == "2024-01-02", "close"].item(), 12)

    def test_too_short_series_stops(self):
        with self.assertRaises(I.DataQualityError):
            I.clean_prices(pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10), "close": 1.0}))

    def test_twse_duplicate_key_stops_instead_of_inflating(self):
        y = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "close": [10.0, 11.0]})
        t = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-02"]), "close_twse": [10.0, 10.0]})
        with self.assertRaises(I.DataQualityError):
            I.crosscheck_twse(y, t, 0.005)

    def test_vix_is_strictly_previous_day(self):
        r = pd.DataFrame({"date": pd.to_datetime(["2024-01-03", "2024-01-04"]), "ret": [0.01, -0.01]})
        v = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
                          "vixcls": [11.0, 12.0, 13.0]})
        out, q = I.attach_vix(r, v)
        self.assertEqual(out["vixcls"].tolist(), [11.0, 12.0])  # never the same-day value
        self.assertEqual(q["rows_out"], 2)

    def test_split_is_chronological(self):
        r = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=100), "ret": np.arange(100.0)})
        a, b = I.time_split(r, 0.7)
        self.assertEqual((len(a), len(b)), (70, 30))
        self.assertLess(a["date"].max(), b["date"].min())
        with self.assertRaises(ValueError):
            I.time_split(r, 1.0)


class TestWorkbookReplica(unittest.TestCase):
    def test_hand_series(self):
        # prices 100,101,100,102 -> returns +1%, -0.990099%, +2%
        b = W.vt_daily_block(np.array([100, 101, 100, 102.0]), period=3)
        r = np.array([0.01, 100 / 101 - 1, 0.02])
        self.assertEqual(b["m"], 3)
        self.assertAlmostEqual(b["sd_window"], r.std(ddof=1), places=15)
        self.assertEqual(b["n_beyond_2sd"], 0)

    def test_sample_is_520_when_period_smaller(self):
        b = W.vt_daily_block(np.linspace(100, 200, 900), period=250)
        self.assertEqual((b["m"], b["w"]), (520, 250))


if __name__ == "__main__":
    unittest.main()
