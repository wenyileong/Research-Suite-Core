# Changelog

## 0.1.0 (23 October 2026)

First version: Phase 1 of the development roadmap and the first part of Phase 2.

- Licence audit of the three existing tools (`docs/licence_audit_2026-10-23.md`). No copyleft code is bundled in any distributed build; the Lab's build should add full third-party licence texts.
- Clean-room process, specification template and inspiration register.
- Data model specification v1, aligned with the International Tax Network Lab's conventions and validation rules.
- `rscore` package (standard library only): conventions, schema of 15 content tables, SQLite store with migrations and validated writes, jurisdiction registry, canonical hashing, snapshot export and verification, and export to the Lab's dataset format.
- 60 tests, including an optional check against the Lab's own importer.
