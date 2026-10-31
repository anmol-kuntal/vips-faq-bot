import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from google.genai import errors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import answer

HERE = Path(__file__).parent
CACHE_FILE = HERE / "cache.json"
PAUSE = 2

REFUSAL_MARKERS = [
    "don't have", "do not have", "does not have", "not covered", "no information",
    "not mentioned", "doesn't include", "does not include", "does not contain",
    "contact the college", "not explicitly", "does not specify", "doesn't specify",
    "only assist", "can only help",
]

def is_refusal(text):
    t = text.lower()
    return any(m in t for m in REFUSAL_MARKERS)


def passes(case, response):
    if case.get("refuse"):
        return is_refusal(response)
    text = response.lower()
    return all(any(alt in text for alt in req.split("|")) for req in case["must_include"])


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def get_response(case, version, cache):
    key = f"{version}:{case['id']}"
    if key in cache:
        return cache[key]
    for attempt in range(8):
        try:
            response = answer(case["question"], version)
            break
        except errors.APIError as e:
            if e.code not in (500, 503, 504) or attempt == 7:
                raise
            wait = 15 * (attempt + 1)
            print(f"  model busy ({e.code}), waiting {wait}s")
            time.sleep(wait)
    cache[key] = response
    save_cache(cache)
    time.sleep(PAUSE)
    return response


def run(version, cases, cache):
    results, by_cat = [], defaultdict(list)
    for case in cases:
        response = get_response(case, version, cache)
        ok = passes(case, response)
        by_cat[case["category"]].append(ok)
        results.append({**case, "response": response, "passed": ok})
    total = sum(r["passed"] for r in results)
    print(f"\n=== Prompt {version}: {total}/{len(cases)} = {100 * total / len(cases):.1f}% ===")
    for cat, oks in by_cat.items():
        print(f"  {cat:13s} {sum(oks)}/{len(oks)}")
    return results


if __name__ == "__main__":
    cases = json.loads((HERE / "test_set.json").read_text(encoding="utf-8"))
    versions = sys.argv[1:] or ["v1", "v2"]
    cache = load_cache()
    all_results = {}
    try:
        for v in versions:
            all_results[v] = run(v, cases, cache)
    except errors.APIError as e:
        print(f"\nStopped on API error {e.code}. Answers so far are saved. Run the same command again later.")
        sys.exit(1)

    out = HERE / "results.json"
    out.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull answers saved to {out}")
    for v, res in all_results.items():
        fails = [r for r in res if not r["passed"]]
        print(f"\nFailures for {v}:")
        for r in fails:
            print(f"  [{r['id']}] {r['question']}\n      -> {r['response'][:150]}")