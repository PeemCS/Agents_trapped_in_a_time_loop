from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from loopday.colab import make_zip, notebook


class ColabExportTest(unittest.TestCase):
    def test_bundle_is_reproducible_and_excludes_credentials_and_replays(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("loopday", "server", "web", "runs"):
                (root / name).mkdir()
            for name in (".env", "loopday/.ignore.py", "server/model.py", "web/viewer.js", "runs/private.json"):
                (root / name).write_text("placeholder")
            first = root / "first.zip"
            second = root / "second.zip"
            self.assertEqual(make_zip(root, first), make_zip(root, second))
            with ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), ["server/model.py", "web/viewer.js"])

    def test_notebook_cells_are_valid_python_and_start_with_model_runs_disabled(self):
        data = notebook("a" * 64)
        self.assertEqual(data["nbformat"], 4)
        self.assertEqual(len({cell["id"] for cell in data["cells"]}), len(data["cells"]))
        for cell in data["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), cell["id"], "exec")
        all_code = "\n".join("".join(cell["source"]) for cell in data["cells"])
        self.assertIn("RUN_CANARY = False", all_code)
        self.assertIn("RUN_FULL = False", all_code)
