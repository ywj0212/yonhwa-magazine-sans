#!/usr/bin/env python3
import faulthandler

from build import build_all

faulthandler.enable(all_threads=True)

if __name__ == "__main__":
    build_all()
