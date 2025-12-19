#!/usr/bin/env python3
import faulthandler
import sys

from pipeline import build_all

faulthandler.enable(all_threads=True)

if __name__ == "__main__":
    try:
        build_all()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", flush=True)
        sys.exit(130)
