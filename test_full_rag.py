# -*- coding: utf-8 -*-
"""Save detailed test results to file for review."""
import requests, json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

URL = "http://localhost:8501/api/chat"
tests = [
    {"name": "컴퓨터공학과", "msg": "컴퓨터공학과 졸업요건 알려줘"},
    {"name": "전자공학과", "msg": "전자공학과 졸업요건 알려줘"},
]

with open("test_results_v2.txt", "w", encoding="utf-8") as out:
    for t in tests:
        data = {"message": t["msg"], "category": "undergrad_rules", "cohort": "2025", "history": []}
        r = requests.post(URL, json=data, timeout=120)
        body = r.json()
        out.write(f'=== {t["name"]} (status={r.status_code}) ===\n')
        out.write(body.get("answer", "NO ANSWER") + "\n")
        out.write(f'Sources: {len(body.get("sources", []))}\n')
        for s in body.get("sources", []):
            out.write(f'  - {s.get("title", "?")}\n')
        out.write("\n\n")

print("Saved to test_results_v2.txt")
