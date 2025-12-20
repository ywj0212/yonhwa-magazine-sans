#!/bin/zsh
source /Users/ywj0212/Desktop/coding/yonhwa-font/venv/bin/activate
export PYTHONPATH="$PWD/src:$PWD/venv/lib/python3.14/site-packages:$PYTHONPATH"
fontforge -lang=py -script ./src/main.py
