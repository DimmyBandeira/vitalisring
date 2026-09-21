#!/bin/bash
# uso: ./snap.sh   -> reconstrói, serve, captura e encerra o servidor
cd "$(dirname "$0")"
python3 build.py >/dev/null || exit 1
python3 -m http.server 8100 --directory dist >/dev/null 2>&1 &
PID=$!; sleep 1
python3 shot.py
kill $PID
