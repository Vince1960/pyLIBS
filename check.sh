#!/bin/bash

echo "Checking syntax..."
python3 -m py_compile pyLIBS_python_prototype_v8_18_incremental_template_update.py

echo
echo "Git status"
git status

echo
echo "Done."
