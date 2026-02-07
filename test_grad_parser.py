# -*- coding: utf-8 -*-
"""Quick unit test for graduation table parsing."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from smart_chunker import rechunk_document, _is_graduation_table

with open(r'docs\undergrad_rules\2025\doc.jsonl', 'r', encoding='utf-8') as f:
    docs = [json.loads(l) for l in f if l.strip()]

# Find the actual table chunk
found = False
for i, d in enumerate(docs):
    c = d['page_content']
    if all(kw in c for kw in ['기본구조표', '컴퓨터공학과', '전자공학과', '130']):
        rechunked = rechunk_document(d)
        for rc in rechunked:
            dept = rc.get('metadata', {}).get('department', '')
            method = rc.get('metadata', {}).get('chunk_method', '')
            if dept == '컴퓨터공학과' and method == 'grad_table_dept':
                print(f'CS: {rc["page_content"]}')
                print()
            if dept == '전자공학과' and method == 'grad_table_dept':
                print(f'EE: {rc["page_content"]}')
                print()
        dept_chunks = [rc for rc in rechunked if rc.get('metadata',{}).get('chunk_method') == 'grad_table_dept']
        print(f'Doc {i}: rechunked into {len(rechunked)} total, {len(dept_chunks)} grad_table_dept')
        found = True
        break

if not found:
    print("No actual grad table doc found!")

# Count total grad table triggers
grad_count = sum(1 for d in docs if _is_graduation_table(d['page_content']))
print(f'\nTotal docs that trigger grad table: {grad_count} out of {len(docs)}')
