# Local literature annotation application

Approved scope: local Python launcher, FastAPI/SQLite, React/TypeScript reader and
annotation form, BioC retrieval, evidence/version provenance, legacy CSV import,
portable exports, backup/restore. No AI extraction, PDF ingestion, hosted accounts,
central paper assignments, or agreement scoring.

Build order: persistence and profile/draft workflow → retrieval and reader →
evidence-linked entry → CSV exchange and recovery → packaging and browser checks.

The article reader uses a white reading surface with serif body text; controls use
system sans-serif, slate text, blue primary actions, and green saved states.
Desktop uses a resizable-feeling two-column reading/editing workspace; narrow
screens stack it. Empty, loading, deferred, error, unsaved, and saved states are
explicit. No external fonts, analytics, or decorative imagery.

Tests: pytest for persistence, retrieval, validation, imports, exports, and recovery;
TypeScript checks and Playwright for critical browser behavior. External retrieval
uses deterministic transport fixtures plus a live connectivity check when possible.

Source references: NCBI BioC API documentation; FastAPI testing/static-files docs;
React useEffect reference; Vite backend integration; Python sqlite3 backup API.
Live NCBI requests initially failed through the restricted network route; both
endpoints were subsequently verified using the documented sample PMID, including
the actual abbreviated BioC section labels.
