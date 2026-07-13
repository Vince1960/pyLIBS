# pyLIBS Development Rules

This repository is the Python rewrite of the historical LIBS++ software.

## General principles
- Preserve the original behaviour of LIBS++ whenever possible.
- Make the smallest possible changes.
- Never rewrite large portions of code unless explicitly requested.
- Keep compatibility with LIBS.db and Stark.db.
- Keep the current GUI layout.
- Preserve menu names and commands.
- Do not rename existing classes or functions unless strictly necessary.

## Coding rules
- Implement one feature at a time.
- Avoid introducing new dependencies.
- Use sqlite3 for database access.
- Store persistent settings in pyLIBS.ini.

## GUI design rules

pyLIBS is a scientific desktop application. Assume a standard working
environment of a 1920x1080 monitor at 100% display scaling.

- Dialogs must open with all controls immediately visible.
- Avoid clipped buttons, clipped labels, clipped tables, clipped plots, excessive margins, and unused space.
- Size dialogs according to content; avoid oversized fixed geometries where practical.
- Do not introduce vertical or horizontal scrollbars in dialog windows.
- If a dialog is crowded, reorganize with Frames, LabelFrames, or ttk.Notebook tabs, or enlarge the window moderately.
- Dialogs containing plots or tables should remain resizable.
- Small utility dialogs, such as Shift, Offset, GoTo, and Statistics, may remain fixed-size.
- Keep visual organization consistent: main content, optional status/information area, then action buttons.
- Keep similar buttons in a consistent order; Close is normally rightmost, Compute precedes Close, and Cancel is used only for editable dialogs.
- Use consistent font family, font size, button height, and padding.
- Window titles must be concise and in English.
- Prefer pack/grid weights, minsize(), update_idletasks(), and requested widget sizes over obsolete oversized geometry strings.
- The Options dialog must not show excessive bottom space, must keep all controls visible, must use pages/tabs when needed, and must preserve single-instance foreground behavior.

## Before finishing any task
Always run:

python -m py_compile pyLIBS.py

## Report
Always report:
- modified files
- summary of changes
- syntax check result

Never modify unrelated code.

## Manual and documentation

- The manual file is stored in docs/pyLIBS_Manual.pdf.
- Treat the manual as the historical functional specification.
- The current pyLIBS implementation may include newer behaviour not documented in the manual.
- When the manual and current code differ, report the discrepancy.
- Never remove newer behaviour only because it is absent from the manual.
- Before modifying a feature, compare:
  1. the manual description;
  2. the current Python implementation;
  3. the requested change.
- Modify only the missing or explicitly requested parts.

## Task workflow

Before modifying code:
1. Verify whether the requested feature already exists.
2. Explain what is already implemented.
3. List missing behaviour.
4. Modify only the missing parts.
5. Run:

python3 -m py_compile pyLIBS.py

6. Report modified files, summary, and syntax-check result.

## Documentation maintenance

When a task changes the project:

- update PROJECT_STATE.md if the project status changes;
- update TODO.md if tasks are completed;
- update CHANGELOG.md if functionality changes;
- update DECISIONS.md only when a new architectural decision is taken;
- update ARCHITECTURE.md only when the software architecture changes.
