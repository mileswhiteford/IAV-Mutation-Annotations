# Decisions
Record all changes and decisions made during the annotation progress. Record the date of the change, what was changed/decided, and why.
### 11/13/2026
- Added the local browser annotation application with independent contributor
  identities, optional registry paper IDs, draft/complete/legacy statuses,
  evidence/source version provenance, CSV exchange, and backup/restore.
- Documented the existing template's `pmid`, `pmcid`, and `notes` fields in the
  prose schema. `author` remains the paper researcher, separate from annotator identity.
- App CSV exports retain template order and add contributor IDs/names, record IDs,
  status, optional email, and review flags. Exported dates use `MM/DD/YYYY`.
  Imports preserve original values/provenance and accept historical date formats.
- Vocabulary collection now reads `date`, with `date_annotated` compatibility,
  and uses exported contributor names when present. `first_seen` uses ISO dates
  so mixed-format historical dates sort chronologically.
- Scientific inclusion rules are unchanged. Existing rows do not need scientific
  reannotation because of these bookkeeping changes. Imported rows remain marked
  for evidence review; no Results evidence is invented for historical records.

### 10/22/2026
- Changed `protocol.md`
  - Include all tested mutations related to host adaptivity, even those which had no effect.
  - All phenotypes should be recorded in comparison to the wildtype phenotype. 
- Changed `schema.md`
  - Added date last updated
  - `mutation`:
    - Specified that mutation phenotypic descriptions should be recorded in comparison to the wildtype phenotype.
  - `animal_model`:
    - Use animal models most simple name instead of specific strain (BALB/c mice --> Mice)
    - Do not report specific tissue. Only report animal model of experiment.


