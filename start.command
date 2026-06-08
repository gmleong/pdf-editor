#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="/Users/gm/.hermes/profiles/agent-2/home/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
exec /Library/Developer/CommandLineTools/usr/bin/python3 main.py
