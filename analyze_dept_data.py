# -*- coding: utf-8 -*-
"""Dump relevant comp sci lines to JSON."""
import json
from pathlib import Path

orig = Path(r"docs\undergrad_rules\2025\doc.jsonl")
with open(orig, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

# Dump lines containing 컴퓨터공학 to JSON
output = []
for i, doc in enumerate(lines):
    content = doc.get("page_content", "")
    if "컴퓨터공학" in content:
        output.append({
            "line": i,
            "length": len(content),
            "content": content,
            "metadata": doc.get("metadata", {})
        })

out_path = Path("cs_data_analysis.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Found {len(output)} docs with 컴퓨터공학. Saved to {out_path}")

# Also dump V2 chunks
v2 = Path(r"docs_v2\undergrad_rules\2025\doc.jsonl")
with open(v2, "r", encoding="utf-8") as f:
    v2docs = [json.loads(l) for l in f if l.strip()]

v2_output = []
for i, d in enumerate(v2docs):
    content = d.get("page_content", "")
    dept = d.get("metadata", {}).get("department", "")
    if "컴퓨터공학" in content or dept in ("컴퓨터공학과", "컴퓨터공학부"):
        v2_output.append({
            "chunk": i,
            "department_tag": dept,
            "method": d.get("metadata", {}).get("chunk_method", "?"),
            "length": len(content),
            "content": content
        })

out_path2 = Path("cs_v2_chunks.json")
with open(out_path2, "w", encoding="utf-8") as f:
    json.dump(v2_output, f, ensure_ascii=False, indent=2)

print(f"V2: {len(v2_output)} chunks. Saved to {out_path2}")
