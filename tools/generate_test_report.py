"""
Runs tests/test_suite.py and writes docs/TEST_REPORT.md (for the project guide / viva).
Usage: python tools/generate_test_report.py
"""
import os, sys, time, unittest, warnings, datetime
warnings.simplefilter("ignore")
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT); os.chdir(ROOT)


class Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.rows = []
    def _add(self, test, status, note=""):
        doc = (test.shortDescription() or str(test)).strip()
        tc, _, desc = doc.partition(":")
        self.rows.append((tc.strip(), desc.strip(), status, note))
    def addSuccess(self, t): super().addSuccess(t); self._add(t, "PASS")
    def addFailure(self, t, e): super().addFailure(t, e); self._add(t, "FAIL", str(e[1])[:80])
    def addError(self, t, e): super().addError(t, e); self._add(t, "ERROR", str(e[1])[:80])


suite = unittest.defaultTestLoader.discover("tests")
runner = unittest.TextTestRunner(resultclass=Collect, stream=open(os.devnull, "w"), verbosity=0)
res = runner.run(suite)
rows = sorted(res.rows)
passed = sum(r[2] == "PASS" for r in rows)
lines = ["# DeepVerif.AI — Automated Test Report", "",
         f"Generated: {datetime.datetime.now():%d %b %Y, %H:%M}  ", f"Result: **{passed}/{len(rows)} passed**", "",
         "| Test ID | What is checked | Result |", "|---|---|---|"]
lines += [f"| {tc} | {d} | {'✅ PASS' if st == 'PASS' else '❌ ' + st + ' ' + n} |" for tc, d, st, n in rows]
lines += ["", "## Model accuracy (see `evaluation/results/`)", "",
          "Run `python evaluation/evaluate_sms.py` and `python evaluation/evaluate_shield.py` and paste the tables here.", "",
          "## Sign-off", "",
          "| Role | Name | Signature | Date |", "|---|---|---|---|",
          "| Tester (student) | | | |", "| Project guide / Sir | | | |"]
out = os.path.join("docs", "TEST_REPORT.md")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print(f"{passed}/{len(rows)} passed -> {out}")
sys.exit(0 if passed == len(rows) else 1)
