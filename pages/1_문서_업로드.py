import os
import re
from datetime import date

import streamlit as st

from db import models
from engine.docx_adapter import DocxDocument
from engine.extractor import extract
from engine.hwpx_adapter import HwpxDocument
from engine.schema import DOC_TYPES

st.set_page_config(page_title="문서 업로드", page_icon="⬆️", layout="wide")
models.init_db()
st.title("⬆️ 문서 업로드")


def _sanitize(name: str) -> str:
    name = re.sub(r"\s+", "", name)
    name = re.sub(r"[^0-9A-Za-z가-힣_\-]", "", name)
    return name or "문서"


doc_type = st.selectbox(
    "업무 종류", list(DOC_TYPES.keys()), format_func=lambda k: DOC_TYPES[k]["label"]
)
uploaded = st.file_uploader("hwpx 또는 docx 파일 업로드", type=["hwpx", "docx"])

if uploaded is not None and "upload_pending" not in st.session_state:
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    base = _sanitize(uploaded.name.rsplit(".", 1)[0])
    suggested_key = f"{doc_type}/{date.today().strftime('%Y%m%d')}_{base}"
    key_widget_id = f"new_doc_key_{doc_type}_{uploaded.name}"
    doc_key = st.text_input("문서 키 (필요하면 수정하세요)", value=suggested_key, key=key_widget_id)

    if st.button("업로드", type="primary"):
        st.session_state["upload_pending"] = {
            "doc_type": doc_type,
            "doc_key": st.session_state[key_widget_id],
            "ext": ext,
            "filename": uploaded.name,
            "bytes": uploaded.getvalue(),
        }
        st.rerun()

pending = st.session_state.get("upload_pending")
if pending:
    if models.key_exists(pending["doc_key"]) and not st.session_state.get("upload_confirmed"):
        st.warning(f"이미 동일한 키 **{pending['doc_key']}** 의 파일이 존재합니다.")
        c1, c2 = st.columns(2)
        if c1.button("취소"):
            del st.session_state["upload_pending"]
            st.rerun()
        if c2.button("새 파일로 저장 (번호 자동 추가)", type="primary"):
            pending["doc_key"] = models.next_available_key(pending["doc_key"])
            st.session_state["upload_pending"] = pending
            st.session_state["upload_confirmed"] = True
            st.rerun()
    else:
        try:
            if pending["ext"] == "hwpx":
                adapter = HwpxDocument.open(pending["bytes"])
            else:
                adapter = DocxDocument.open(pending["bytes"])
            field_data = extract(adapter, pending["doc_type"])
        except Exception as exc:
            st.error(f"파일 분석에 실패했습니다: {exc}")
            if st.button("다시 시도"):
                del st.session_state["upload_pending"]
                st.session_state.pop("upload_confirmed", None)
                st.rerun()
        else:
            storage_dir = os.path.join("storage", pending["doc_type"])
            os.makedirs(storage_dir, exist_ok=True)
            safe_name = pending["doc_key"].replace("/", "_")
            source_path = os.path.join(storage_dir, f"{safe_name}.{pending['ext']}")
            with open(source_path, "wb") as f:
                f.write(pending["bytes"])
            doc_id = models.insert_document(
                pending["doc_key"], pending["doc_type"], pending["filename"],
                pending["ext"], source_path, field_data,
            )
            st.success(f"저장되었습니다: **{pending['doc_key']}** (id={doc_id})")
            st.info("'문서 관리/편집' 메뉴에서 내용을 확인·수정할 수 있습니다.")
            del st.session_state["upload_pending"]
            st.session_state.pop("upload_confirmed", None)
