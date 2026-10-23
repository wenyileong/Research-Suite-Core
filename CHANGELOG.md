# Changelog

## 0.2.0 (23 October 2026)

- Suite launcher, `ResearchSuite.exe`: one window that finds the three tools (saved location, beside or inside the launcher's folder, the usual install folder, or the registry) and opens them; Locate saves a tool's location; English and Simplified Chinese interface; settings in `%APPDATA%\ResearchSuite\launcher.json`.
- Suite icon, with its editable SVG source and a script that redraws every size.
- Windows packaging: PyInstaller specification with version information, third-party notices generated from the build environment, `build_windows.bat`, and a GitHub Actions workflow that tests, builds, smoke-tests and uploads the exe.
- Third-party notices fall back to the official Tcl and Tk licence texts (`packaging/licences/`) where the build Python does not ship them, as on GitHub's Windows runners for Tcl.
- Test workflow on Python 3.11 to 3.13. 70 tests in all.

## 0.1.0 (23 October 2026)

First version: Phase 1 of the development roadmap and the first part of Phase 2.

- Licence audit of the three existing tools (`docs/licence_audit_2026-10-23.md`). No copyleft code is bundled in any distributed build; the Lab's build should add full third-party licence texts.
- Clean-room process, specification template and inspiration register.
- Data model specification v1, aligned with the International Tax Network Lab's conventions and validation rules.
- `rscore` package (standard library only): conventions, schema of 15 content tables, SQLite store with migrations and validated writes, jurisdiction registry, canonical hashing, snapshot export and verification, and export to the Lab's dataset format.
- 60 tests, including an optional check against the Lab's own importer.
