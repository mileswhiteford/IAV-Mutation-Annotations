"""Bundle authoritative resources and the prebuilt UI into Python distributions."""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).parent


class BuildApplication(build_py):
    def run(self):
        if not (ROOT / "src/iav_annotator/static/index.html").is_file():
            raise RuntimeError("Build the frontend first: cd frontend; npm ci; npm run build")
        super().run()
        resources = Path(self.build_lib) / "iav_annotator/resources"
        for name in ("protocol.md", "decisions.md", "papers.csv", "schema", "vocab", "annotations"):
            source = ROOT / name
            target = resources / name
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


setup(cmdclass={"build_py": BuildApplication})
