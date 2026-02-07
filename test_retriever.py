"""검색 테스트"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API key
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

from chains import get_vector_store, get_retriever_chain

# Test
print("Loading vector store...")
vs = get_vector_store("undergrad_rules", "2025")
print("Creating retriever...")
retriever = get_retriever_chain(vs, top_k=5)

print("\nTesting search: '전자공학과 졸업요건'")
docs = retriever.invoke("전자공학과 졸업요건")
print(f"Got {len(docs)} documents\n")

for i, doc in enumerate(docs):
    content = doc.page_content[:200]
    korean_chars = sum(1 for c in content if '\uac00' <= c <= '\ud7a3')
    total_chars = len(content.replace(" ", "").replace("\n", ""))
    kr_ratio = korean_chars / max(total_chars, 1)
    print(f"[{i+1}] Korean ratio: {kr_ratio:.2%}")
    print(f"    Content: {content[:100]}...")
    print()
