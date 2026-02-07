"""
Smart Document Re-chunker for KHU Regulations Chatbot
=====================================================
기존 ~2000자 고정 청킹 JSONL → 의미 단위 분할:
  1) 학과별 섹션 분할 (졸업학점표 등)
  2) 조항(제N조) 단위 분할
  3) 표/구조 데이터 보존
  4) 오버랩 포함 적정 크기 분할
"""
import json
import re
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional

# ─────────────────────────────────────────────────────────────────────
# 패턴 정의
# ─────────────────────────────────────────────────────────────────────

# 조항 패턴: 제1조, 제15조의2 등
ARTICLE_RE = re.compile(r"(제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*\([^)]*\))?)")

# 학과명 패턴
DEPARTMENT_NAMES = [
    "기계공학과", "산업경영공학과", "원자력공학과", "화학공학과",
    "신소재공학과", "정보전자신소재공학과",
    "사회기반시스템공학과", "건축공학과", "건축학과",
    "환경학및환경공학과", "환경학및환경공학과",
    "전자공학과", "반도체공학과", "전자정보공학부",
    "생체의공학과",
    "컴퓨터공학과", "컴퓨터공학부", "인공지능학과", "소프트웨어융합학과",
    "응용수학과", "응용물리학과", "응용화학과", "우주과학과",
    "스마트팜과학과", "식물·환경신소재공학과", "식물환경신소재공학과",
    "식품생명공학과", "원예생명공학과", "유전생명공학과",
    "한방생명공학과", "융합바이오·신소재공학과", "융합바이오신소재공학과",
    "국제학과", "아시아학과",
    # 대학 단위
    "공과대학", "전자정보대학", "소프트웨어융합대학",
    "응용과학대학", "생명과학대학", "국제대학",
    "외국어대학", "문과대학", "이과대학",
]

# 졸업학점 관련 테이블 키워드
GRAD_TABLE_KEYWORDS = [
    "졸업학점", "전공학점", "전공기초", "전공필수", "전공선택",
    "교육과정 기본구조표", "단일전공과정", "다전공과정", "부전공과정",
]

# 교양 교과 관련 키워드
LIBERAL_ARTS_KEYWORDS = [
    "교양교과", "배분이수", "자유이수", "중핵교과", "후마니타스",
    "교양교육과정",
]

# 섹션 구분 패턴
SECTION_HEADERS = re.compile(
    r"(Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ|Ⅷ|Ⅸ|Ⅹ)\.\s*"
)

# ─────────────────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────────────────

def _count_depts(text: str) -> List[str]:
    """텍스트에 포함된 학과명 목록 반환"""
    found = []
    for dept in DEPARTMENT_NAMES:
        if dept in text:
            found.append(dept)
    return found


def _is_graduation_table(text: str) -> bool:
    """실제 졸업학점 기본구조표인지 판단 (엄격한 조건).
    단순히 '졸업학점'이 언급된 시행세칙 등은 제외.
    조건: '기본구조표' 포함 + 졸업 관련 키워드 3개+ + 학과명 5개+ 나열
    """
    if "기본구조표" not in text:
        return False
    score = sum(1 for kw in GRAD_TABLE_KEYWORDS if kw in text)
    if score < 3:
        return False
    # 실제 테이블이면 다수(5+) 학과명이 나열되어야 함
    dept_count = sum(1 for d in DEPARTMENT_NAMES if d in text and "대학" not in d)
    return dept_count >= 5


def _has_articles(text: str) -> bool:
    """조항 패턴 포함 여부"""
    matches = ARTICLE_RE.findall(text)
    return len(matches) >= 2


def _make_chunk(content: str, base_metadata: dict, extra_meta: dict = None) -> dict:
    """새 청크 생성"""
    meta = copy.deepcopy(base_metadata)
    if extra_meta:
        meta.update(extra_meta)
    meta["chunk_method"] = extra_meta.get("chunk_method", "smart") if extra_meta else "smart"
    return {
        "page_content": content.strip(),
        "metadata": meta,
    }


# ─────────────────────────────────────────────────────────────────────
# 대학-학과 매핑 (졸업학점표 파싱용)
# ─────────────────────────────────────────────────────────────────────

# 학과 → 소속대학
DEPT_TO_COLLEGE = {
    "기계공학과": "공과대학", "산업경영공학과": "공과대학",
    "원자력공학과": "공과대학", "화학공학과": "공과대학",
    "신소재공학과": "공과대학", "정보전자신소재공학과": "공과대학",
    "사회기반시스템공학과": "공과대학", "건축공학과": "공과대학",
    "건축학과": "공과대학", "환경학및환경공학과": "공과대학",
    "전자공학과": "전자정보대학", "반도체공학과": "전자정보대학",
    "전자정보공학부": "전자정보대학", "생체의공학과": "전자정보대학",
    "컴퓨터공학과": "소프트웨어융합대학", "컴퓨터공학부": "소프트웨어융합대학",
    "인공지능학과": "소프트웨어융합대학", "소프트웨어융합학과": "소프트웨어융합대학",
    "응용수학과": "응용과학대학", "응용물리학과": "응용과학대학",
    "응용화학과": "응용과학대학", "우주과학과": "응용과학대학",
    "스마트팜과학과": "생명과학대학", "식물·환경신소재공학과": "생명과학대학",
    "식물환경신소재공학과": "생명과학대학",
    "식품생명공학과": "생명과학대학", "원예생명공학과": "생명과학대학",
    "유전생명공학과": "생명과학대학", "한방생명공학과": "생명과학대학",
    "융합바이오·신소재공학과": "생명과학대학", "융합바이오신소재공학과": "생명과학대학",
    "국제학과": "국제대학", "아시아학과": "국제대학",
}

# 졸업학점표 컬럼 헤더
GRAD_TABLE_HEADER = "대학명 / 학과(전공) / 졸업학점 / 전공기초 / 전공필수 / 전공선택"

# ─────────────────────────────────────────────────────────────────────
# 분할 전략
# ─────────────────────────────────────────────────────────────────────

def _parse_graduation_table_rows(text: str) -> List[Dict[str, Any]]:
    """
    졸업학점표의 flat-text를 파싱하여 학과별 행 데이터 추출.
    졸업학점표는 PDF에서 추출 시 flat sequence로 나열됨:
      '공과대학 기계공학과 130 18 산업경영공학과 130 24 ...'
    
    핵심 전략:
    - 각 학과명의 **모든** 출현 위치를 찾음
    - 뒤에 오는 숫자 중 졸업학점이 100~160 범위인 것만 채택
    - DEPT_TO_COLLEGE 매핑으로 정확한 소속대학 배정
    - 동일 학과 중복 제거 (가장 정보가 많은 것 선택)
    """
    # Only dept-level names (not colleges)
    dept_only = [d for d in DEPARTMENT_NAMES if "대학" not in d]
    
    best_rows: Dict[str, Dict[str, Any]] = {}  # dept -> best row
    
    for dept in dept_only:
        # Find ALL occurrences of this department name
        start = 0
        while True:
            idx = text.find(dept, start)
            if idx < 0:
                break
            start = idx + len(dept)
            
            # Extract numbers immediately after dept name (within 40 chars)
            after = text[idx + len(dept):idx + len(dept) + 40]
            numbers = re.findall(r"\d+", after)
            
            if not numbers:
                continue
            
            grad_credits = int(numbers[0])
            
            # 핵심 검증: 졸업학점은 반드시 100~160 범위
            # (경희대 모든 학과 졸업학점은 120~156)
            if grad_credits < 100 or grad_credits > 160:
                continue
            
            # 소속대학은 DEPT_TO_COLLEGE 매핑 사용 (정확도 우선)
            college = DEPT_TO_COLLEGE.get(dept, "")
            
            row = {
                "department": dept,
                "college": college,
                "grad_credits": grad_credits,
            }
            
            # 전공기초: 다음 숫자, 50 이하만 유효
            if len(numbers) >= 2:
                major_basic = int(numbers[1])
                if major_basic <= 50:
                    row["major_basic"] = major_basic
            
            # 전공필수: 그 다음 숫자, 50 이하만 유효 + 다음학과 졸업학점과 구분
            if len(numbers) >= 3:
                n = int(numbers[2])
                if n <= 50:
                    row["major_required"] = n
            
            # 더 많은 정보가 있는 행을 선택 (dedup)
            if dept not in best_rows or len(row) > len(best_rows[dept]):
                best_rows[dept] = row
    
    return list(best_rows.values())


def split_graduation_table(content: str, base_meta: dict) -> List[dict]:
    """
    졸업학점표를 학과별 구조화된 청크로 분할.
    각 청크에 대학명, 학과명, 학점 정보를 명시적으로 포함.
    """
    rows = _parse_graduation_table_rows(content)
    
    if not rows:
        # 테이블 파싱 실패 시 원본 그대로 유지
        return [_make_chunk(content, base_meta, {"chunk_method": "grad_table_whole"})]
    
    chunks = []
    
    # 연도 정보 추출 (metadata에서 가져오거나 텍스트에서 추정)
    year = base_meta.get("cohort", "")
    if not year:
        year_match = re.search(r"(20\d{2})학년도", content)
        year = year_match.group(1) if year_match else "2025"
    
    # 각 학과별 구조화된 청크 생성 (원본은 포함하지 않음 — 중복 최소화)
    for row in rows:
        dept = row["department"]
        college = row.get("college", "")
        
        # 구조화된 텍스트 청크 (검색 최적화)
        lines = []
        lines.append(f"{year}학년도 전공별 교육과정 기본구조표")
        lines.append(f"소속 대학: {college}")
        lines.append(f"학과/전공: {dept}")
        if row.get("grad_credits"):
            lines.append(f"졸업학점: {row['grad_credits']}학점")
        if row.get("major_basic"):
            lines.append(f"전공기초: {row['major_basic']}학점")
        if row.get("major_required"):
            lines.append(f"전공필수: {row['major_required']}학점")
        
        chunk_text = "\n".join(lines)
        chunks.append(_make_chunk(
            chunk_text, base_meta,
            {
                "department": dept,
                "college": college,
                "section_type": "graduation_credits",
                "chunk_method": "grad_table_dept",
            }
        ))
    
    return chunks


def split_by_department(content: str, base_meta: dict) -> List[dict]:
    """
    학과명을 기준으로 텍스트를 분할.
    졸업학점표는 특별 처리, 그 외는 라인 기반 분할.
    """
    # 졸업학점표 감지 → 특별 처리
    if _is_graduation_table(content):
        return split_graduation_table(content, base_meta)
    
    depts = _count_depts(content)
    if len(depts) < 2:
        return [_make_chunk(content, base_meta, {"chunk_method": "dept_single"})]

    chunks = []
    lines = content.split("\n")

    # 학과별로 관련 라인 수집
    current_dept = None
    dept_lines: Dict[str, List[str]] = {}
    header_lines = []  # 학과명 앞의 헤더 라인

    for line in lines:
        found_dept = None
        for dept in depts:
            if dept in line:
                found_dept = dept
                break

        if found_dept:
            current_dept = found_dept
            if current_dept not in dept_lines:
                dept_lines[current_dept] = list(header_lines)  # 헤더 포함
            dept_lines[current_dept].append(line)
        elif current_dept:
            dept_lines[current_dept].append(line)
        else:
            header_lines.append(line)

    # 각 학과별 청크 생성
    for dept, d_lines in dept_lines.items():
        chunk_content = "\n".join(d_lines).strip()
        if len(chunk_content) > 50:  # 너무 짧은 건 무시
            college = DEPT_TO_COLLEGE.get(dept, "")
            chunks.append(_make_chunk(
                chunk_content, base_meta,
                {"department": dept, "college": college, "chunk_method": "dept_split"}
            ))

    # 학과에 속하지 않는 헤더/일반 내용
    if header_lines:
        header_content = "\n".join(header_lines).strip()
        if len(header_content) > 100:
            chunks.append(_make_chunk(
                header_content, base_meta,
                {"section_type": "header", "chunk_method": "dept_header"}
            ))

    return chunks if chunks else [_make_chunk(content, base_meta)]


def split_by_article(content: str, base_meta: dict) -> List[dict]:
    """조항(제N조) 단위로 분할"""
    parts = ARTICLE_RE.split(content)
    chunks = []
    current_article = None

    i = 0
    while i < len(parts):
        part = parts[i].strip()

        if ARTICLE_RE.match(part):
            current_article = part
            # 다음 파트가 본문
            if i + 1 < len(parts):
                body = parts[i + 1].strip()
                article_text = f"{current_article}\n{body}"
                # 조 번호 추출
                m = re.search(r"(\d+)", current_article)
                art_num = int(m.group(1)) if m else None
                chunks.append(_make_chunk(
                    article_text, base_meta,
                    {
                        "articleNumber": art_num,
                        "section_type": "article",
                        "chunk_method": "article_split",
                    }
                ))
                i += 2
                continue
            i += 1
        else:
            # 조항 앞의 서문
            if part and len(part) > 50:
                chunks.append(_make_chunk(
                    part, base_meta,
                    {"section_type": "preamble", "chunk_method": "article_preamble"}
                ))
            i += 1

    return chunks if chunks else [_make_chunk(content, base_meta)]


def split_with_overlap(content: str, chunk_size: int = 1000, overlap: int = 200,
                       base_meta: dict = None) -> List[dict]:
    """오버랩 포함 크기 기반 분할 (문장 경계 존중)"""
    if base_meta is None:
        base_meta = {}

    # 문장 단위로 분리
    sentences = re.split(r"(?<=[.。!?]\s)", content)
    if not sentences:
        return [_make_chunk(content, base_meta, {"chunk_method": "overlap"})]

    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len > chunk_size and current:
            chunk_text = "".join(current)
            chunks.append(_make_chunk(
                chunk_text, base_meta, {"chunk_method": "overlap_split"}
            ))
            # 오버랩: 마지막 몇 문장 유지
            overlap_text = ""
            keep = []
            for s in reversed(current):
                if len(overlap_text) + len(s) <= overlap:
                    keep.insert(0, s)
                    overlap_text = "".join(keep)
                else:
                    break
            current = keep
            current_len = len(overlap_text)

        current.append(sent)
        current_len += sent_len

    if current:
        chunks.append(_make_chunk(
            "".join(current), base_meta, {"chunk_method": "overlap_split"}
        ))

    return chunks


# ─────────────────────────────────────────────────────────────────────
# 메인 재청킹 로직
# ─────────────────────────────────────────────────────────────────────

def rechunk_document(doc: dict) -> List[dict]:
    """
    단일 문서를 스마트하게 재분할.
    전략 우선순위:
      1. 졸업학점표 → 학과별 분할
      2. 여러 학과 포함 → 학과별 분할
      3. 조항 포함 → 조항별 분할
      4. 긴 문서 → 오버랩 분할
      5. 짧은 문서 → 그대로 유지
    """
    content = doc.get("page_content", "")
    metadata = doc.get("metadata", {})

    if not content or len(content) < 50:
        return []

    # Source prefix 제거 (중복 방지)
    # "Source : 파일명.pdf\n" 형태의 prefix는 metadata에 이미 있으므로 본문에서 제거 않음
    # (검색에 도움이 되므로 유지)

    depts = _count_depts(content)

    # 전략 1: 졸업학점표 → 학과별 분할
    if _is_graduation_table(content) and len(depts) >= 3:
        return split_by_department(content, metadata)

    # 전략 2: 여러 학과 포함 (3개 이상) → 학과별 분할
    if len(depts) >= 3:
        return split_by_department(content, metadata)

    # 전략 3: 조항 포함 → 조항별 분할
    if _has_articles(content):
        article_chunks = split_by_article(content, metadata)
        # 조항 분할 후 너무 긴 청크가 있으면 추가 분할
        final = []
        for chunk in article_chunks:
            if len(chunk["page_content"]) > 1500:
                final.extend(split_with_overlap(
                    chunk["page_content"], 1000, 200, chunk["metadata"]
                ))
            else:
                final.append(chunk)
        return final

    # 전략 4: 긴 문서 → 오버랩 분할
    if len(content) > 1500:
        return split_with_overlap(content, 1000, 200, metadata)

    # 전략 5: 그대로 유지
    return [_make_chunk(content, metadata, {"chunk_method": "passthrough"})]


def rechunk_jsonl(input_path: Path, output_path: Path) -> dict:
    """
    JSONL 파일을 스마트하게 재청킹.
    Returns stats dict.
    """
    # Load original
    original_docs = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    original_docs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Rechunk
    new_docs = []
    method_counts: Dict[str, int] = {}

    for doc in original_docs:
        chunks = rechunk_document(doc)
        for chunk in chunks:
            method = chunk.get("metadata", {}).get("chunk_method", "unknown")
            method_counts[method] = method_counts.get(method, 0) + 1
            new_docs.append(chunk)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in new_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # Stats
    orig_lengths = [len(d.get("page_content", "")) for d in original_docs]
    new_lengths = [len(d.get("page_content", "")) for d in new_docs]

    stats = {
        "original_count": len(original_docs),
        "new_count": len(new_docs),
        "original_avg_len": sum(orig_lengths) / max(len(orig_lengths), 1),
        "new_avg_len": sum(new_lengths) / max(len(new_lengths), 1),
        "new_min_len": min(new_lengths) if new_lengths else 0,
        "new_max_len": max(new_lengths) if new_lengths else 0,
        "method_counts": method_counts,
    }
    return stats


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Smart re-chunking of JSONL documents")
    ap.add_argument("input", help="Input JSONL file path")
    ap.add_argument("output", help="Output JSONL file path")
    args = ap.parse_args()

    stats = rechunk_jsonl(Path(args.input), Path(args.output))
    print(f"Original: {stats['original_count']} docs (avg {stats['original_avg_len']:.0f} chars)")
    print(f"Re-chunked: {stats['new_count']} docs (avg {stats['new_avg_len']:.0f} chars)")
    print(f"  Min: {stats['new_min_len']}, Max: {stats['new_max_len']}")
    print(f"  Methods: {stats['method_counts']}")


if __name__ == "__main__":
    main()
