import os
import sys
import json
import urllib.request
from pathlib import Path

# Autoload .env
env_file = Path(__file__).resolve().parent.parent / ".env"
tavily_key = ""
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("TAVILY_API_KEY="):
            tavily_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not tavily_key:
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()

if not tavily_key:
    print("[FAIL] TAVILY_API_KEY not found in .env or environment")
    sys.exit(1)

print(f"[INFO] Found TAVILY_API_KEY: {tavily_key[:8]}...{tavily_key[-4:]}")

url = "https://api.tavily.com/search"
payload = json.dumps({
    "api_key": tavily_key,
    "query": "Skydrol LD-4 hydraulic fluid friction coefficient MSDS",
    "search_depth": "basic",
    "max_results": 3
}).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json", "User-Agent": "AetherLoop-Verifier/1.0"}
)

try:
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode("utf-8"))
        results = body.get("results", [])
        print(f"[PASS] HTTP {status_code} received from https://api.tavily.com/search")
        print(f"[PASS] Retrieved {len(results)} grounded search citations:")
        for idx, item in enumerate(results, start=1):
            title = item.get("title", "No Title")
            url_item = item.get("url", "")
            print(f"  {idx}. {title} ({url_item})")
        sys.exit(0)
except urllib.error.HTTPError as e:
    print(f"[FAIL] HTTP {e.code}: {e.read().decode('utf-8')}")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Connection error: {e}")
    sys.exit(1)
