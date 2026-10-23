# Clean-room process

Open-source projects supply ideas, methods and test results to this suite; they never supply text. This folder holds the evidence that each component built from an open-source idea was written independently.

## Why

Copyright in a program protects its expression, not the ideas, principles, functionality, programming language or data formats behind it (Directive 2009/24/EC, art 1(2); Case C-406/10 *SAS Institute Inc v World Programming Ltd* EU:C:2012:259; *SAS Institute Inc v World Programming Ltd* [2013] EWCA Civ 1482; *Navitaire Inc v easyJet Airline Co Ltd* [2004] EWHC 3487 (Ch)). Independent creation answers a claim of infringement, so the process exists to make independent creation provable. It reduces risk; it does not create immunity.

AI coding tools can reproduce code they have seen. The main control is therefore keeping reference source code out of the session that writes our code.

## When it applies

| Reference licence | Treatment |
| --- | --- |
| Copyleft (GPL, AGPL, LGPL where linking is in doubt) | Clean-room only. Running the reference privately as a test oracle is fine. |
| Permissive (MIT, BSD, Apache, ISC) | May be a dependency with its notice kept, or rebuilt clean-room where a lighter build helps. |
| Unknown or none | Treat as copyleft: read for the approach only. |
| Published academic method (no code consulted) | No clean-room file needed; cite the method in the code's documentation. |
| The author's own repositories | Not third-party code; reuse is permitted. Record the origin in the commit message. |

Data is separate. A clean room covers code only. Rate tables, case-law corpora and fixtures are governed by database right and the source's terms, and no test data or fixtures are copied from copyleft repositories.

## The four stages

1. **Study.** Read the project's paper and documentation, and its code only where needed. Prefer the published method wherever one exists.
2. **Specify.** Write a specification in your own words, using `TEMPLATE.md`: purpose, inputs, outputs, algorithm steps in plain language or neutral pseudocode, edge cases and the citation of the method. Copy no code, identifiers, comments or docstrings. Add or update the row in `../inspiration_register.csv`.
3. **Implement.** In a fresh AI session, give the specification only. Never paste reference source code into an implementation session, and never ask the AI to recreate a named library from memory.
4. **Verify.** Run the reference privately on shared test inputs and compare outputs. Check our code for copied structure, names or comments before committing. Record the result in the component's file.

## Files

- `TEMPLATE.md`: the specification template.
- `<component>.md`: one file per clean-room component (specification, register entry, verification result).
- `../inspiration_register.csv`: every open-source reference, its licence and how it is used.
