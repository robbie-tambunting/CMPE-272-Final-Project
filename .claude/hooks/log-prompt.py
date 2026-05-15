#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime

data = json.load(sys.stdin)
prompt = data.get("prompt", "").strip()
if not prompt:
    sys.exit(0)

project_root = os.environ.get("CLAUDE_PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
notes_path = os.path.join(project_root, "AI-NOTES.md")

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

entry = f"\n### {timestamp} — {model}\n\n{prompt}\n"

with open(notes_path, "a") as f:
    f.write(entry)
