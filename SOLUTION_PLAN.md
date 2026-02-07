# 🎯 컴퓨터공학과 검색 문제 - 최종 진단 및 해결 방안

## 📊 문제 요약

**증상**: "컴퓨터공학과 졸업요건" 질문 → 공과대학 자료로 잘못 답변  
**원인**: 2가지 복합적 문제

---

## 🔍 Root Cause Analysis

### 1️⃣ **FAISS 인덱스 손상** (치명적) 🔴

**현상:**
```bash
$ file faiss_db/undergrad_rules/2025/index.faiss
> ASCII text  # 정상이면 "data" 또는 binary

$ head index.faiss
> version https://git-lfs.github.com/spec/v1
> oid sha256:fca8fb046f2853ad1b99abca4fce487661f79605a561977...
```

**원인:**
- Git LFS 포인터 파일만 commit됨 (실제 바이너리는 LFS 서버에)
- 실제 133 bytes (정상은 수 MB)
- FAISS 로드 시 `Index type not recognized` 에러

**영향:**
- ❌ 모든 벡터 검색 실패
- ❌ RAG 파이프라인 완전 중단

---

### 2️⃣ **데이터 커버리지 부족** (구조적) 🟡

**현황 분석:**
```bash
$ grep -i "컴퓨터" docs/undergrad_rules/2025/doc.jsonl | wc -l
> 3개 (공과대학 교육과정.pdf에서만 언급)
```

**문제점:**
- ❌ 컴퓨터공학과 전용 문서 없음
- ❌ 전자정보대학 교육과정 누락
- ✅ 공과대학 교육과정만 존재 (기계, 화공, 건축 등)

**학과-단과대학 매핑:**
```
컴퓨터공학과    → 전자정보대학 ✅
전자공학과      → 전자정보대학 ✅  
소프트웨어융합  → 전자정보대학 ✅

기계공학과      → 공과대학 ⚠️
화학공학과      → 공과대학 ⚠️
```

**현재 상황:**
- 컴퓨터공학과 질문 → 공과대학 문서 검색 → ❌ 잘못된 답변

---

## 🛠️ 해결 방안

### ✅ Solution 1: FAISS 인덱스 재구축 (필수)

#### 방법 A: rebuild_smart.py 사용 (권장)
```bash
cd /home/user/webapp

# 1. OpenAI API 키 설정
export OPENAI_API_KEY="sk-..."

# 2. 인덱스 재구축
python rebuild_smart.py

# 예상 소요 시간: 10-30분
# 예상 비용: $1-5 (OpenAI embedding API)
```

**장점:**
- ✅ 스마트 청킹으로 품질 향상
- ✅ 기존 docs/ 데이터 활용
- ✅ 모든 연도 인덱스 일괄 재구축

#### 방법 B: rebuild_faiss.py 사용 (빠름)
```bash
cd /home/user/webapp
python rebuild_faiss.py

# 더 빠르지만 스마트 청킹 없음
```

#### 방법 C: Git LFS 다운로드 (네트워크 필요)
```bash
# Git LFS 설치
apt-get install git-lfs  # 또는 brew install git-lfs
git lfs install

# 인덱스 다운로드
git lfs pull --include="faiss_db/**/*.faiss"
git lfs pull --include="faiss_db/**/*.pkl"

# 예상 다운로드: 500MB - 2GB
```

---

### ✅ Solution 2: 누락 문서 추가 (중요)

#### 필요 문서:
1. **전자정보대학 교육과정.pdf** (2025년도)
2. 각 학과별 개별 시행세칙
   - 컴퓨터공학과 시행세칙.pdf
   - 전자공학과 시행세칙.pdf
   - 소프트웨어융합학과 시행세칙.pdf

#### 추가 방법:
```bash
# 1. 문서를 todo_documents/에 배치
mkdir -p todo_documents/undergrad_rules/2025
# 파일 복사: 전자정보대학_교육과정.pdf

# 2. 문서 인덱싱
python add_document.py --category undergrad_rules --cohort 2025

# 3. 인덱스 확인
python verify_faiss.py
```

---

### ✅ Solution 3: RAG 파이프라인 개선 (선택)

#### A. Query Router 통합 (빠른 파싱)
```python
# backend/routers/chat.py에 추가
from query_router import query_router

# 학과명 자동 인식
meta_filter, hints = query_router(request.message)
# → "컴퓨터공학과" 인식 → department filter 적용
```

#### B. 메타데이터 필터 강화
```python
# 문서 메타데이터에 단과대학 정보 추가
{
  "college": "전자정보대학",
  "department": "컴퓨터공학과",
  "cohort": "Cohort_2025"
}

# 검색 시 필터 적용
meta_filter = {
  "department": "컴퓨터공학과"
}
```

#### C. BM25 키워드 부스팅
```python
# reranker.py에서 학과명 완전 일치 시 부스트
if query_department == doc.metadata.get("department"):
    score += 0.5  # 큰 가중치
```

---

## 📋 Action Plan

### Phase 1: 긴급 복구 (오늘 중) ⚡
```bash
# Step 1: API 키 설정
export OPENAI_API_KEY="your-key"

# Step 2: 인덱스 재구축
python rebuild_smart.py

# Step 3: 테스트
python diagnose_search.py

# 예상 시간: 30분 - 1시간
```

**예상 결과:**
- ✅ 검색 기능 복구
- ⚠️ 여전히 공과대학 문서 검색 (데이터 문제)

---

### Phase 2: 데이터 보완 (1-3일) 📚
```bash
# Step 4: 전자정보대학 문서 추가
# - 전자정보대학 교육과정.pdf 확보
# - todo_documents/undergrad_rules/2025/ 에 배치

# Step 5: 재인덱싱
python add_document.py --category undergrad_rules --cohort 2025

# Step 6: 검증
python verify_faiss.py
grep -i "컴퓨터공학과" docs/undergrad_rules/2025/doc.jsonl | wc -l
# → 50+ 건 이상이면 OK
```

**예상 결과:**
- ✅ 컴퓨터공학과 전용 데이터
- ✅ 올바른 답변 제공

---

### Phase 3: 알고리즘 최적화 (1주) 🎯
```python
# Step 7: Query Router 통합
# Step 8: 메타데이터 필터 강화
# Step 9: Reranker 튜닝
# Step 10: A/B 테스트
```

**예상 결과:**
- ✅ 검색 정확도 90%+
- ✅ 학과 구분 정확도 95%+
- ✅ 사용자 만족도 향상

---

## 💰 비용 추정

### OpenAI API 비용
- Embedding (text-embedding-3-large): $0.13 / 1M tokens
- 예상 문서 크기: ~5M tokens (전체 재인덱싱)
- **예상 비용: $0.65 - $5**

### 개발 시간
- Phase 1 (긴급): 1-2시간
- Phase 2 (데이터): 4-8시간
- Phase 3 (최적화): 16-24시간

---

## 🎯 핵심 요약

### 문제
1. **FAISS 인덱스 손상** → 검색 불가
2. **데이터 부족** → 잘못된 답변

### 해결
1. **인덱스 재구축** → `rebuild_smart.py`
2. **문서 추가** → 전자정보대학 교육과정
3. **알고리즘 개선** → Query Router + 메타필터

### 우선순위
1. ⚡ Phase 1 (긴급): 인덱스 재구축
2. 📚 Phase 2 (중요): 데이터 보완
3. 🎯 Phase 3 (선택): 알고리즘 최적화

---

## 🚀 즉시 실행 가능한 명령어

```bash
# 현재 디렉토리 확인
cd /home/user/webapp

# API 키가 있다면:
export OPENAI_API_KEY="sk-..."
python rebuild_smart.py

# API 키가 없다면 (관리자에게 요청):
# 1. GitHub에서 Git LFS 파일 다운로드
# 2. 전자정보대학 교육과정 문서 확보
# 3. add_document.py로 추가
```

---

**다음 단계를 알려주시면 바로 진행하겠습니다!** 🎯
