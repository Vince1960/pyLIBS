# pyLIBS Project State

**Project:** pyLIBS (Python rewrite of LIBS++)
**Current version:** v8.18
**Git branch:** main

---

# Project goals

The purpose of pyLIBS is to reproduce the behaviour of the historical
LIBS++ software while modernising the codebase in Python.

General principles:

- preserve the original behaviour whenever possible;
- improve the code without changing the user interface;
- keep compatibility with LIBS.db;
- keep compatibility with historical templates;
- implement one feature at a time.

---

# Current status

## Completed

- Conversion from LIBS++ to Python started.
- Main GUI implemented.
- Spectrum display.
- Zoom and pan.
- Multiple spectra.
- Template management.
- Manual line identification.
- Automatic line identification.
- Trace Lines.
- Incremental template update.
- Voigt fitting.
- Multi-Gaussian fitting.
- GoTo command.
- GridX/GridY persistence.
- LogX/LogY persistence.
- Background colour persistence.
- Last directory persistence.
- Git repository created.
- Codex development environment configured.

---

# Verified

✓ pyLIBS.ini loading

✓ pyLIBS.ini saving

✓ Git workflow

✓ Codex integration

---

# Known issues

- Duplicate definitions of
  - load_pylibs_ini()
  - save_pylibs_ini()
  - show_startup_splash()

- Very large single Python source file (~15k lines)

- Stark.db not yet fully integrated

- Some GUI functions still require verification against the original manual.

---

# Development workflow

Before every modification:

1. Read AGENTS.md
2. Read PROJECT_STATE.md
3. Read TODO.md
4. Read the LIBS++ manual if relevant.
5. Compare implementation with the manual.
6. Modify only the requested functionality.
7. Run

python3 -m py_compile pyLIBS_python_prototype_v8_18_incremental_template_update.py

8. Report

- modified files
- summary
- syntax check

---

# Next task

Verify the current implementation of Analyse → Find Peaks
against the original LIBS++ manual.

Do not modify code until the comparison has been completed.

---

# Session log

## 2026-06-26

- Git repository created.
- Codex CLI installed.
- AGENTS.md created.
- TODO.md created.
- LIBS++ manual added.
- Fixed legacy pyLIBS.ini parsing bug.
- View preferences persistence verified.

# Decision Log

## 2026-06-26

Decision:
Keep pyLIBS.ini compatible with the historical positional format.

Reason:
Maintain compatibility with existing installations and legacy configuration files.

---

Decision:
Incremental template updates replace the old overwrite behaviour.

Reason:
More convenient for interactive analysis.

---

Decision:
Use Git + Codex as the standard development workflow.

Reason:
Every modification becomes traceable and reversible.
