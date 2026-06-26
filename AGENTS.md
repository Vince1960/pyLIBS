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

## Before finishing any task
Always run:

python -m py_compile pyLIBS_python_prototype_v8_18_incremental_template_update.py

## Report
Always report:
- modified files
- summary of changes
- syntax check result

Never modify unrelated code.
