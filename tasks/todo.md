# Implementation checklist

- [x] Local package, profile, persistent drafts, and stale-edit protection
- [x] Independent BioC retrieval, cached source versions, and section-aware reader
- [x] Evidence-linked form, duplication, validation, and autosave
- [x] Legacy imports, portable exports, backups, and restoration
- [x] Documentation, distributable wheel, API contract generation, and browser checks

Verification: 30 backend tests; five real Chrome workflows; axe scan with zero
violations on the annotation screen; 320/768/1024/1440 layout checks; live PubMed
and PMC BioC sample retrieval; isolated wheel installation/launcher smoke test;
Ruff and TypeScript checks; zero production npm advisories. An inverted evidence
guard was detected by its regression test, then the original source was restored
and the full backend suite passed.

The real virologist pilot remains an external acceptance activity. Automated
fixtures and UI checks do not establish scientific annotation quality.
