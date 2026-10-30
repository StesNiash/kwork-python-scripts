import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from routools.cli import main
from routools.csv_report import build_report
from routools.dedupe import apply_quarantine, find_duplicates
from routools.rename import apply_plan, build_plan


class DedupeTests(unittest.TestCase):
    def test_finds_duplicate_content_and_keeps_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("same", encoding="utf-8")
            (root / "b.txt").write_text("same", encoding="utf-8")
            (root / "c.txt").write_text("different", encoding="utf-8")
            groups = find_duplicates(root)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].keep.name, "a.txt")
            self.assertEqual([path.name for path in groups[0].duplicates], ["b.txt"])

    def test_apply_moves_duplicates_to_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            (work / "a.txt").write_text("same", encoding="utf-8")
            (work / "b.txt").write_text("same", encoding="utf-8")
            groups = find_duplicates(work)
            moved = apply_quarantine(groups, root / "quarantine")
            self.assertEqual(len(moved), 1)
            self.assertFalse((work / "b.txt").exists())
            self.assertTrue((root / "quarantine" / "b.txt").exists())
            self.assertTrue((work / "a.txt").exists())

    def test_different_sizes_are_not_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("x", encoding="utf-8")
            (root / "b.txt").write_text("xx", encoding="utf-8")
            self.assertEqual(find_duplicates(root), [])


class RenameTests(unittest.TestCase):
    def test_plan_and_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            plans = build_plan(root, "doc_{n:02d}{suffix}")
            self.assertEqual([plan.target.name for plan in plans], ["doc_01.txt", "doc_02.txt"])
            apply_plan(plans)
            self.assertTrue((root / "doc_01.txt").exists())
            self.assertTrue((root / "doc_02.txt").exists())

    def test_rejects_duplicate_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_plan(root, "same{suffix}")


class CsvReportTests(unittest.TestCase):
    def test_counts_clean_and_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text(
                " name , city \n"
                " Alice , Moscow \n"
                " Bob , Kazan \n"
                " Alice , Moscow \n"
                " , \n",
                encoding="utf-8",
            )
            report = build_report(path)
            self.assertEqual(report["columns"], ["name", "city"])
            self.assertEqual(report["rows"], 3)
            self.assertEqual(report["blank_rows"], 1)
            self.assertEqual(report["duplicate_rows"], 1)
            self.assertEqual(report["empty_cells"], 0)


class CliTests(unittest.TestCase):
    def test_dedupe_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("same", encoding="utf-8")
            (root / "b.txt").write_text("same", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["dedupe", str(root), "--json"])
            self.assertEqual(code, 0)
            self.assertIn('"duplicates": 1', buffer.getvalue())

    def test_csv_report_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b\n1,2\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["csv-report", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("rows: 1", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
