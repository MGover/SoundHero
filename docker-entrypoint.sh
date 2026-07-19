#!/bin/sh
set -e

python - <<'PY'
import importlib
missing = []
for module in ['discord', 'nacl', 'yt_dlp', 'requests', 'dotenv']:
    try:
        importlib.import_module(module)
    except Exception as exc:
        missing.append(f"{module}: {exc}")

if missing:
    raise SystemExit("Missing Python dependencies:\n" + "\n".join(missing))

print("Dependency check passed.")
PY

exec python sound-hero.py
