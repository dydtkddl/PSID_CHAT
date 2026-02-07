"""FAISS 인덱스 진단 스크립트"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API key from .streamlit/secrets.toml
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
        if "OPENAI_API_KEY" in secrets:
            os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import tempfile
import shutil
from pathlib import Path
from collections import Counter

def diagnose_faiss_index(category: str, cohort: str = None):
    """FAISS 인덱스에 포함된 문서들을 분석"""
    
    base = Path(__file__).parent / "faiss_db" / category
    if cohort:
        cohort_path = base / str(cohort)
        if (cohort_path / "index.faiss").exists():
            base = cohort_path
    
    index_path = base / "index.faiss"
    pkl_path = base / "index.pkl"
    
    if not index_path.exists():
        print(f"❌ Index not found: {index_path}")
        return
    
    print(f"📂 Loading index from: {base}")
    
    # 임시 디렉토리로 복사 (한글 경로 문제 우회)
    temp_dir = tempfile.mkdtemp(prefix="faiss_diag_")
    try:
        shutil.copy2(str(index_path), os.path.join(temp_dir, "index.faiss"))
        if pkl_path.exists():
            shutil.copy2(str(pkl_path), os.path.join(temp_dir, "index.pkl"))
        
        store = FAISS.load_local(
            temp_dir,
            embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
            allow_dangerous_deserialization=True
        )
        
        # 문서 분석
        docs = list(store.docstore._dict.values())
        print(f"\n📊 Total documents: {len(docs)}")
        
        # 소스 파일별 통계
        sources = []
        languages = {"korean": 0, "english": 0, "mixed": 0}
        
        for doc in docs:
            meta = doc.metadata
            source = meta.get("source") or meta.get("filename") or meta.get("title") or "Unknown"
            sources.append(source)
            
            # 언어 감지 (간단한 휴리스틱)
            content = doc.page_content[:500]
            korean_chars = sum(1 for c in content if '\uac00' <= c <= '\ud7a3')
            english_chars = sum(1 for c in content if 'a' <= c.lower() <= 'z')
            
            if korean_chars > english_chars * 2:
                languages["korean"] += 1
            elif english_chars > korean_chars * 2:
                languages["english"] += 1
            else:
                languages["mixed"] += 1
        
        # 소스 파일 통계
        source_counts = Counter(sources)
        print(f"\n📁 Unique sources: {len(source_counts)}")
        print("\n🔝 Top 20 sources:")
        for src, count in source_counts.most_common(20):
            print(f"  [{count:3d}] {src[:80]}")
        
        # 언어 통계
        print(f"\n🌍 Language distribution:")
        print(f"  Korean:  {languages['korean']:4d} ({languages['korean']/len(docs)*100:.1f}%)")
        print(f"  English: {languages['english']:4d} ({languages['english']/len(docs)*100:.1f}%)")
        print(f"  Mixed:   {languages['mixed']:4d} ({languages['mixed']/len(docs)*100:.1f}%)")
        
        # 영어 문서 샘플 (문제 있는 문서)
        if languages["english"] > 0:
            print(f"\n⚠️ English document samples (potential issues):")
            count = 0
            for doc in docs:
                content = doc.page_content[:200]
                korean_chars = sum(1 for c in content if '\uac00' <= c <= '\ud7a3')
                english_chars = sum(1 for c in content if 'a' <= c.lower() <= 'z')
                if english_chars > korean_chars * 2:
                    print(f"\n  Source: {doc.metadata.get('source', 'Unknown')[:60]}")
                    print(f"  Content: {content[:150]}...")
                    count += 1
                    if count >= 5:
                        break
        
        # 검색 테스트
        print("\n\n🔍 Search test: '전자공학과 졸업요건'")
        results = store.similarity_search("전자공학과 졸업요건", k=5)
        for i, r in enumerate(results):
            print(f"\n  [{i+1}] Source: {r.metadata.get('source', 'Unknown')[:60]}")
            print(f"      Content: {r.page_content[:150]}...")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import io
    import sys
    
    # Capture output to file
    output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = output
    
    # undergrad_rules/2025 진단
    diagnose_faiss_index("undergrad_rules", "2025")
    
    sys.stdout = old_stdout
    result = output.getvalue()
    
    # Save to file
    with open("diagnosis_result.txt", "w", encoding="utf-8") as f:
        f.write(result)
    
    print("✅ Diagnosis complete! Results saved to diagnosis_result.txt")
    print(result)
