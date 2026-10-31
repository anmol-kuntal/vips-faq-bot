import json
from pathlib import Path
from run_eval import REFUSAL_MARKERS

HERE = Path(__file__).parent
cases = json.loads((HERE / "test_set.json").read_text(encoding="utf-8"))
cache = json.loads((HERE / "cache.json").read_text(encoding="utf-8"))

only = {}
for c in cases:
    if not c.get("refuse"):
        continue
    for v in ("v1", "v2", "v3"):
        resp = cache.get(f"{v}:{c['id']}")
        if resp is None:
            continue
        hits = [m for m in REFUSAL_MARKERS if m in resp.lower()]
        if len(hits) == 1:
            only.setdefault(hits[0], []).append((v, c["id"], resp[:100]))

for m in REFUSAL_MARKERS:
    print(f"{m!r}: needed for {len(only.get(m, []))} answer(s)")
    for v, i, r in only.get(m, []):
        print(f"    {v} [{i}] {r}")