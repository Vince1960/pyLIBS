#!/bin/bash

echo "Checking syntax..."
python3 -m py_compile pyLIBS.py

echo
echo "Git status"
git status

echo
echo "Done."
