"""Test the smart chunker output quality."""
import json
from pathlib import Path
from collections import Counter

v2 = Path(r"docs_v2\undergrad_rules\2025\doc.jsonl")
docs = [json.loads(l) for l in open(v2, "r", encoding="utf-8") if l.strip()]

lengths = [len(d["page_content"]) for d in docs]
print(f"Total: {len(docs)}, Avg: {sum(lengths)//len(lengths)}, Min: {min(lengths)}, Max: {max(lengths)}")

methods = Counter(d.get("metadata", {}).get("chunk_method", "?") for d in docs)
print("\nChunk methods:")
for m, c in methods.most_common():
    print(f"  {m}: {c}")

dept_docs = [d for d in docs if d.get("metadata", {}).get("department")]
print(f"\nDept-tagged: {len(dept_docs)}")
for d in dept_docs[:10]:
    dept = d["metadata"]["department"]
    clen = len(d["page_content"])
    print(f"  [{dept}] len={clen}")

# Check if 전자공학과 has dedicated chunks
elec = [d for d in docs if d.get("metadata", {}).get("department") == "전자공학과"]
print(f"\n전자공학과 dedicated chunks: {len(elec)}")
for d in elec:
    preview = d["page_content"][:150].replace("\n", " ")
    print(f"  len={len(d['page_content'])}: {preview}")

# Check if 컴퓨터공학과 has dedicated chunks
cs = [d for d in docs if d.get("metadata", {}).get("department") == "컴퓨터공학과"]
print(f"\n컴퓨터공학과 dedicated chunks: {len(cs)}")
for d in cs:
    preview = d["page_content"][:150].replace("\n", " ")
    print(f"  len={len(d['page_content'])}: {preview}")

# Content match check
elec_all = [d for d in docs if "전자공학과" in d["page_content"]]
print(f"\n전자공학과 mention in content: {len(elec_all)}")
