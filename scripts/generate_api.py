"""Generate the OpenAPI input used by npm run types (no persistent database)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iav_annotator.app import create_app

(ROOT / ".artifacts").mkdir(exist_ok=True)
database = ROOT / ".artifacts" / "api-contract.sqlite3"
specification = create_app(database).openapi()
(ROOT / "frontend" / "openapi.json").write_text(json.dumps(specification), encoding="utf-8")
database.unlink()
