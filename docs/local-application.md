# Local annotation application

The app stores work on each annotator's computer. It accepts any PMID, records
who contributed each observation, and exports partial as well as completed work.
No paper assignments, account service, or model API keys are required.

## Install and launch

Annotators need Python 3.11 or newer and a supplied application wheel. Install it
with `python -m pip install /path/to/iav_annotator-0.1.0-py3-none-any.whl`, then run:

```text
iav-annotate
```

The launcher opens a browser at an automatically chosen `127.0.0.1` port. Leave
the terminal running while annotating; press Ctrl+C to stop. The next launch
uses the same database. On Windows, the default database is
`%LOCALAPPDATA%\IAVAnnotator\annotations.sqlite3`; elsewhere it is
`~/.local/share/IAVAnnotator/annotations.sqlite3`.

Optional arguments:

```text
iav-annotate --database /path/to/work.sqlite3 --port 8765 --no-browser
```

Enter your name on first use; email is optional. The **Paper researcher** field
is the schema's `author`, not the annotator. Editing a contributed record keeps
its original attribution; its revision history records the current editor.

## Annotate a paper

1. Enter a PMID. Previously opened papers use cached text; **Retrieve / refresh
   text** explicitly checks NCBI again. The two retrieval statuses are independent.
2. Start an observation and select supporting Results text. Click **Attach Results
   evidence** below that passage. With no selection, the entire passage is used;
   this also works with keyboard navigation. Methods text can be attached separately.
3. Fill the form using the field guidance. **Reuse context** starts a record with
   the same experimental context; **Duplicate observation** also copies the mutation,
   phenotype, and notes. Both start as drafts without evidence.
4. Edits autosave. **Save now** saves immediately. **Mark complete** checks required
   fields, mutation notation, and Results evidence; **Save as draft** preserves
   incomplete work, including after a failed completion attempt.
5. Open **Paper progress and screening notes** to defer a paper, record no eligible
   observations, or mark reading finished. These are independent of record status.

Abstract-only papers support screening and notes. The current scientific protocol
requires Results evidence from full text for completed observations. If section
metadata is uncertain, the app asks you to confirm the selected text's section.
It does not infer unreported experimental details or decide scientific inclusion.

**Show in article** reopens the exact cached source version and checks the saved
quotation. A source refresh preserves old versions and their evidence anchors.
Text/captions supplied by BioC are shown; figures, PDFs, and supplements are not
downloaded. Use the original-article links for material absent from BioC.

If saving fails, keep the tab open and retry. Navigation and export first attempt
to save pending edits. A stale revision from another tab stops automatic saving;
copy your unsaved text before reloading and reconciling the edit manually.

## Import and export

**Import & backup** previews CSVs before importing. Supply the contributor name
for older CSVs without annotator columns. **Preview existing repository annotations**
loads the two bundled historical CSVs (66 observations), identifying their annotators
by folder. All newly imported CSV records require evidence review; malformed field
values remain visible with warnings. Invalid PMIDs, missing attribution, malformed
dates, or conflicting existing IDs prevent the file from being applied.

Import matches columns by header, not order. It accepts `MM/DD/YYYY`, `YYYY.MM.DD`,
and `YYYY-MM-DD`, and accepts the older `date_annotated` column. Original CSV
values and import file hashes remain in provenance. Reimporting an identical file
skips existing records; separate annotators' observations are retained separately.

**Export work** downloads a ZIP:

| File | Contents |
| --- | --- |
| `annotations.csv` | Canonical schema columns followed by observation ID, annotator ID/name, status, optional email, and review flag; dates use `MM/DD/YYYY` |
| `papers.csv` | Paper metadata and contributor-attributed progress/screening notes |
| `provenance.json` | Full observation records, revision/edit attribution, evidence anchors, source passages/version hashes, and rule/vocabulary snapshots |
| `README.txt` | Exchange conventions |

The default export includes drafts, legacy records, flagged observations, and
completed work. **Export completed only** filters observation rows; paper screening
notes remain included. Check `status` and `review_flag` before downstream use.

CSV reimport preserves record IDs and contributor identity, but cannot restore
evidence anchors or revision history. New CSV imports of completed rows become
legacy rows until evidence is attached. Retain the complete export bundle for
collaboration and provenance; use backups to restore the complete application.
No automatic merging or agreement measurement is performed.

## Backup and restore

**Download backup** creates a consistent SQLite snapshot containing all work,
cached article responses, evidence, profiles, and revision history. **Restore an
application backup** validates it, asks before replacing local work, and saves
the previous database beside the current file as `*.before-restore.sqlite3`.
Keep periodic backups outside the working computer. Exports and backups contain
the contributor names/emails entered in the app.

## Develop and package

From the repository root, install Python dependencies and generate the API contract:

```text
python -m pip install -e ".[dev]"
python scripts/generate_api.py
```

In `frontend/`:

```text
npm ci
npm run types
npm run build
```

Node is a developer/build dependency only. The generated TypeScript definitions
come from FastAPI's OpenAPI contract. During UI development, run the backend on
port 8765 and `npm run dev` in `frontend/`; Vite proxies `/api` to the backend.
Open the Vite address for HMR. For the bundled app, run `iav-annotate` after building.

Checks:

```text
python -m pytest -q
python -m ruff check src tests scripts/generate_api.py setup.py
```

From `frontend/`, run `npm run typecheck` and `npm run test:e2e`. The browser tests
use installed Google Chrome, a separate headless profile, fictional article fixtures,
and a fresh database under `.artifacts/`; they do not contact NCBI. They exercise
the full browser workflow and run an axe accessibility scan. Run `npm run build`
after frontend changes so tests use current bundled assets.

To build the wheel after building the UI:

```text
python -m build --wheel
```

The build hook includes compiled browser assets and snapshots of the protocol,
schema, registry, vocabulary mappings, and historical CSVs. It refuses to produce
a wheel without the UI. Changes to those repository resources take effect in an
editable checkout; rebuild the wheel to distribute updated resources. Existing
observations keep the hashes of the rules used for each saved revision. Restart
the app after changing repository rules or mappings so each session uses a fixed
set of guidance and resource hashes.

## Implementation notes and sources

The app uses SQLite transactions with versioned observation snapshots, immutable
source passages, and revision checks. It listens only on loopback and rejects
cross-origin writes. Article text is rendered as text rather than injected HTML.
Database version 1 is initialized automatically; newer unknown versions are rejected.

- [PubMed BioC API](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PubMed/)
- [PMC BioC API](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [React effect cleanup and synchronization](https://react.dev/reference/react/useEffect)
- [Vite backend integration](https://vite.dev/guide/backend-integration)
- [SQLite backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)

Both endpoints were checked with the documented sample PMID during implementation,
including actual section metadata abbreviations. Fixture tests also verify failure
states and source-version behavior. A real annotator pilot with available full
text and an abstract-only paper remains a deployment acceptance activity;
automated tests do not establish scientific annotation quality.
