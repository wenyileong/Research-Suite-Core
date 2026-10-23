# Interface guidelines

The Research Suite window is where the suite is used. These rules keep it complete and intuitive as the suite grows. Tests enforce the first three; the rest are for review.

## Rules the tests enforce

1. **One capability, one service.** Every capability is a function in `src/rscore/services.py` first. The command line (`python -m rscore`) and the window both call it; neither holds logic of its own.
2. **Every command has a window action.** A new command is added to `services.COMMANDS`, to the command line, and to `GUI_ACTIONS` in `src/rscore/launcher/app.py` with the page and method that offer it. `tests/test_interface.py` fails if any of the three is missing.
3. **Every word in the window exists in every language.** Text lives in `src/rscore/launcher/i18n.py`, in English (British) and Simplified Chinese, with the same placeholders. Every rejection reason the importer can give has a plain-language label in both. Interface text uses no em or en dashes.
4. **The window must build.** The self-test (`ResearchSuite.exe --self-test`) opens every page in both languages, imports the invented example release, and uses review, data, snapshot and check. It runs in the test workflow under a virtual display and on the packaged exe in the Windows build, so a page that fails stops the build.

## Rules for review

5. **Every page says what it is for.** A page opens with its title and one sentence of purpose (`title_<page>`, `intro_<page>`).
6. **Guide the next step.** After an action, say what happened in the status line and offer the obvious next step as a button (for example *Review 3 items* after an import). The Tools page keeps the four-step guide current.
7. **Nothing is decided silently.** Where the software cannot decide (a jurisdiction, an assumption), it asks on the Review page or behind an explicit option with a line explaining the trade-off. Assumptions are recorded in the report.
8. **Every value leads to its source.** Tables of data let the user open the source document of a row (double-click, or *Open source document*).
9. **Long work runs in the background.** Anything that can take more than a moment runs through `App.run_in_background`, with progress in the status line, so the window never freezes.
10. **No personal names.** Natural persons are never shown, stored or written to a report.
11. **Look before release.** Screenshot every page in both languages at the default size (1100 by 720) and check that nothing is cut off or overflows. Pages whose content can grow use `ScrollArea`.

## Adding a page

1. Add the key to `PAGES` and a `Page` subclass to `PAGE_CLASSES` in `app.py`.
2. Add `nav_`, `title_` and `intro_` text, and any other keys, to both languages.
3. Add the page to the self-test's walk (it visits every page in `PAGES` automatically) and, if it offers a command, to `GUI_ACTIONS`.
4. Run `xvfb-run -a python -m pytest` (or `python -m pytest` on Windows) and take the screenshots.
