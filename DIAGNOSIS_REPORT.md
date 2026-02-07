# 🔴 **검색 품질 문제 진단 결과**

## 발견된 문제점

### 1️⃣ **FAISS 인덱스 손상 문제** ⚠️
- **증상**: `Index type 0x73726576 ("vers") not recognized` 에러
- **원인**: FAISS 파일이 Git LFS 포인터 파일로 저장됨 (실제 바이너리가 아님)
- **파일 크기**: 133 bytes (정상 파일은 MB 단위)
- **영향**: **모든 검색 기능 작동 불가**

### 2️⃣ **데이터 커버리지 문제** 📊
- **현재 상황**: 2025년도 문서가 "공과대학 교육과정.pdf"만 존재
- **문제점**: 컴퓨터공학과는 **전자정보대학**인데 **공과대학** 문서를 검색
- **결과**: 잘못된 정보 제공 (공과대학 ≠ 전자정보대학)

```
컴퓨터공학과 → 전자정보대학 (정답)
기계공학과, 화학공학과 → 공과대학
```

---

## 🔧 해결 방안

### ✅ **즉시 해결 (우선순위 1)**

#### A. FAISS 인덱스 재구축
```bash
# docs/에서 인덱스 재생성
cd /home/user/webapp
python rebuild_faiss.py

# 또는 rebuild_smart.py 사용 (더 나은 청킹)
python rebuild_smart.py
```

**효과:**
- ✅ 검색 기능 즉시 복구
- ✅ 벡터 검색 정상 작동
- ⏱️ 소요 시간: 10-30분

---

#### B. Git LFS 파일 다운로드
```bash
# Git LFS 설치 및 파일 풀
git lfs install
git lfs pull

# 특정 디렉토리만 풀
git lfs pull --include="faiss_db/**"
```

**주의:**
- 파일 크기가 매우 클 수 있음 (수백 MB ~ GB)
- 네트워크 대역폭 필요

---

### ✅ **데이터 품질 개선 (우선순위 2)**

#### C. 누락된 문서 추가

**필요한 문서:**
1. 전자정보대학 교육과정 (컴퓨터공학과, 전자공학과, 소프트웨어융합학과)
2. 각 단과대학별 교육과정
3. 개별 학과 시행세칙

**방법:**
```bash
# 1. 문서를 todo_documents/undergrad_rules/2025/ 에 배치
# 2. add_document.py 실행
python add_document.py --category undergrad_rules --cohort 2025
```

---

### ✅ **검색 알고리즘 개선 (우선순위 3)**

#### D. 하이브리드 검색 강화

**현재 문제점:**
- 학과명 키워드 매칭 로직은 있지만, FAISS 인덱스 자체가 손상되어 작동 안 함
- 벡터 검색만으로는 학과명 구분 어려움

**개선 방안:**

1. **메타데이터 필터링 강화**
```python
# chains.py의 retriever에 학과명 필터 추가
meta_filter = {
    "college": "전자정보대학",  # 단과대학
    "department": "컴퓨터공학과"  # 학과
}
```

2. **BM25 키워드 부스팅**
```python
# reranker.py에서 학과명에 높은 가중치
if "컴퓨터공학과" in doc.page_content:
    score += 0.5  # 큰 부스트
```

3. **Query Router 통합** (앞서 제안한 기능)
```python
from query_router import query_router

# 빠른 regex 기반 파싱
meta, hints = query_router("컴퓨터공학과 졸업요건")
# hints에 department 정보 포함
```

---

## 📋 실행 계획

### Phase 1: 긴급 복구 (오늘 중)
```bash
# Step 1: FAISS 인덱스 재구축
cd /home/user/webapp
python rebuild_smart.py  # 또는 rebuild_faiss.py

# Step 2: 테스트
python diagnose_search.py
```

### Phase 2: 데이터 보완 (1-2일)
```bash
# Step 3: 누락 문서 추가
# - 전자정보대학 교육과정.pdf
# - 기타 단과대학 문서들

# Step 4: 재인덱싱
python add_document.py --category undergrad_rules --cohort 2025
```

### Phase 3: 알고리즘 개선 (3-5일)
```python
# Step 5: Query Router 통합
# Step 6: 메타데이터 필터링 강화
# Step 7: BM25 부스팅 조정
```

---

## 🎯 기대 효과

### 즉시 효과 (Phase 1)
- ✅ 검색 기능 복구
- ✅ 벡터 검색 작동

### 단기 효과 (Phase 2)
- ✅ 올바른 단과대학 문서 검색
- ✅ 컴퓨터공학과 정확한 답변

### 중장기 효과 (Phase 3)
- ✅ 검색 정확도 90%+ 달성
- ✅ 학과별 정확한 답변
- ✅ 사용자 만족도 향상

---

## 💡 추가 권장 사항

### 1. 메타데이터 표준화
```json
{
  "college": "전자정보대학",
  "department": "컴퓨터공학과",
  "cohort": "Cohort_2025",
  "document_type": "교육과정"
}
```

### 2. 문서 품질 검증
```bash
# validate_metadata.py 실행
python validate_metadata.py --dir docs/undergrad_rules/2025
```

### 3. 정기 인덱스 검증
```bash
# verify_faiss.py로 품질 체크
python verify_faiss.py
```

---

## ❓ 다음 단계

어떤 방안부터 진행할까요?

1. **즉시 복구**: rebuild_smart.py 실행
2. **Git LFS 다운로드**: git lfs pull
3. **데이터 보완**: 누락 문서 추가
4. **전체 개선**: 순차적 진행

선택해주시면 바로 구현하겠습니다! 🚀
