import streamlit as st

from db import models
from engine.schema import DOC_TYPES

st.set_page_config(page_title="SVI 제출서류 관리", page_icon="📄", layout="wide")
models.init_db()

st.title("📄 SVI 제출서류 관리")
st.caption("주식회사 더느린걸음 · 사회적가치지표(SVI) 제출서류 5종 업로드·편집·출력")

st.markdown("왼쪽 메뉴에서 **문서 업로드**, **문서 관리/편집**, **LLM 설정**으로 이동하세요.")

st.divider()
st.subheader("저장된 문서")

col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("키 검색", placeholder="예: 20260910_회의록")
with col2:
    doc_type_filter = st.selectbox(
        "업무 종류", ["전체"] + list(DOC_TYPES.keys()),
        format_func=lambda k: "전체" if k == "전체" else DOC_TYPES[k]["label"],
    )

docs = models.list_documents(
    doc_type=None if doc_type_filter == "전체" else doc_type_filter,
    search=search or None,
)

if not docs:
    st.info("저장된 문서가 없습니다. '문서 업로드' 메뉴에서 시작하세요.")
else:
    for d in docs:
        label = DOC_TYPES[d["doc_type"]]["label"]
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"**{d['doc_key']}**  \n{label}")
            c2.caption(f"원본: {d['original_filename']} ({d['original_format']})")
            c3.caption(f"수정: {d['updated_at']}")
