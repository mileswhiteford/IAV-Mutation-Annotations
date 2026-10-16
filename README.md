# IAV-Mutation-Annotations

Shared protocol, schema, and standardized vocabulary for annotation. Annotations live in separate folders per annotator.

| File / folder | What it is |
|---|---|
| `protocol.md` | Current annotation rules |
| `schema/schema.csv` | Schema template |
| `schema/schema.md` | Feild definitions |
| `decisions.md` | Dated log of every change to the protocol, schema, or vocabulary. Newest first. |
| `vocab/` | Folder for each field we are standardizing, containing combined vocab from annotations and standardized vocab mapping |
| `annotations/<name>/` | Each annotator's CSVs |
| `scripts/` | Helper scripts |

Progress is tracked in the pinned **Annotation progress** issue.

## Workflow

1. Annotate in your own sheet, recording the date in `date_annotated`.
2. Flag any rows that need review.
3. Name file as corresponding paper ID (e.g. P001)
4. Download as CSV (**File → Download → Comma-separated values**).
5. Upload to your folder: **Add file → Upload files**, drag in, commit.


## Making a change

Add a dated entry at the top of `DECISIONS.md` with what changed, why,
and whether already-annotated rows need re-checking. Note it in the
commit message too.

`protocol.md` always holds the current rules. Since every row has a date, the rules a row followed are the entries dated before it. Always update the date in `protocol.md` after any changes are made. 

## Vocabulary

There is a folder for each field we are trying to standardize vocabulary for. Each folder contains `raw.csv` and `standard.csv`. 
- `raw.csv`: Combined list of every value we annotate for that field, the number of times it was recorded, and who recorded it.
- `standard.csv`: Mapping of raw values to agreed-upon standardized values. 
