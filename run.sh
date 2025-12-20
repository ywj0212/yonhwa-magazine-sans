#!/bin/zsh
source ./venv/bin/activate
export PYTHONPATH="$PWD/src:$PWD/venv/lib/python3.14/site-packages:$PYTHONPATH"
fontforge -lang=py -script ./src/main.py
