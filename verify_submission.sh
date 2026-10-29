#!/usr/bin/env bash
set -euo pipefail

echo "=== AETHER-LOOP ZERO-DISQUALIFICATION PRE-SUBMISSION AUDIT ==="

# 1. Verify root LICENSE file exists and contains valid Apache-2.0 text
if [ ! -f "LICENSE" ] || ! grep -qiE "(Apache License|MIT License|Mozilla Public License)" LICENSE; then
  echo "[FAIL] Missing or invalid root LICENSE file! Add Apache-2.0 LICENSE immediately."
  exit 1
fi
echo "[PASS] Root LICENSE file present and verified."

# 2. Verify zero // TODO or FIXME placeholders in codebase
if grep -rnIE "(// TODO|# TODO|FIXME)" backend/ frontend/src/ 2>/dev/null; then
  echo "[FAIL] Found unresolved TODO/FIXME placeholders!"
  exit 1
fi
echo "[PASS] Zero placeholder comments in backend/ and frontend/src/."

# 3. Verify mandatory configuration templates and core modules exist
for req_file in "README.md" ".env.example" "docker-compose.yml" "backend/main.py" "backend/router_nemotron.py" "backend/nebius_serverless.py" "backend/openshell_gate.py" "tests/test_tools_ci.py" "frontend/src/App.tsx"; do
  if [ ! -f "$req_file" ]; then
    echo "[FAIL] Missing required file: $req_file"
    exit 1
  fi
done
echo "[PASS] All core architecture files verified."

# 4. Run deterministic CI tool tests without LLM flakiness
export PATH="$(pwd)/.venv/Scripts:$(pwd)/.venv/bin:$PATH"
export PYTHONPATH=".:${PYTHONPATH:-}"
pytest tests/test_tools_ci.py -v
echo "[PASS] All deterministic HTTP, Newton-Euler physics, and schema tests passed."
echo "=== READY FOR GRAND PRIZE SUBMISSION ==="

