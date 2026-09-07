import glob
import io
import os
import shutil
import zipfile

import streamlit as st

from db import models
from engine.renderer import render_document
from engine.schema import DOC_TYPES
from engine.validation import validate
from ui.editors import render_appointment_editor, render_table_doc_editor


def _photo_dir(doc_key: str) -> str:
    return os.path.join("storage", "photos", doc_key.replace("/", "_"))

st.set_page_config(page_title="문서 관리/편집", page_icon="📝", layout="wide")
models.init_db()
st.title("📝 문서 관리 / 편집")

col1, col2 = st.columns([2, 1])
search = col1.text_input("키 검색")
type_filter = col2.selectbox(
    "업무 종류", ["전체"] + list(DOC_TYPES.keys()),
    format_func=lambda k: "전체" if k == "전체" else DOC_TYPES[k]["label"],
)

docs = models.list_documents(doc_type=None if type_filter == "전체" else type_filter, search=search or None)
if not docs:
    st.info("문서가 없습니다. '문서 업로드' 메뉴에서 먼저 업로드하세요.")
    st.stop()

labels = [f"{d['doc_key']}  —  {DOC_TYPES[d['doc_type']]['label']}  (수정: {d['updated_at']})" for d in docs]
idx = st.selectbox("문서 선택", range(len(docs)), format_func=lambda i: labels[i])
doc_row = docs[idx]
doc_id = doc_row["id"]
doc_type = doc_row["doc_type"]

state_key = f"field_data_{doc_id}"
if state_key not in st.session_state:
    st.session_state[state_key] = models.get_document(doc_id)["field_data"]
field_data = st.session_state[state_key]

photo_key = f"photos_{doc_id}"
if photo_key not in st.session_state:
    loaded = {}
    for path in glob.glob(os.path.join(_photo_dir(doc_row["doc_key"]), "*.jpg")):
        slot = os.path.splitext(os.path.basename(path))[0]
        with open(path, "rb") as f:
            loaded[slot] = f.read()
    st.session_state[photo_key] = loaded
photo_files = st.session_state[photo_key]

st.subheader(f"{doc_row['doc_key']} — {DOC_TYPES[doc_type]['label']}")

if doc_type == "위촉장":
    render_appointment_editor(field_data, key_prefix=f"doc{doc_id}")
else:
    render_table_doc_editor(doc_type, field_data, photo_files, key_prefix=f"doc{doc_id}")

warnings = validate(doc_type, field_data)
if warnings:
    with st.container(border=True):
        st.markdown("**확인 필요 사항** (저장/출력을 막지는 않습니다)")
        for w in warnings:
            st.warning(w)

st.divider()
if st.button("💾 저장", type="primary"):
    models.update_field_data(doc_id, field_data)
    photo_dir = _photo_dir(doc_row["doc_key"])
    os.makedirs(photo_dir, exist_ok=True)
    for stale in glob.glob(os.path.join(photo_dir, "*.jpg")):
        os.remove(stale)
    for slot, content in photo_files.items():
        with open(os.path.join(photo_dir, f"{slot}.jpg"), "wb") as f:
            f.write(content)
    st.success("저장되었습니다.")

st.divider()
st.subheader("출력")
fmt_label = st.radio("출력 포맷", ["HWPX", "DOCX"], horizontal=True, key=f"doc{doc_id}_fmt")
fmt = "hwpx" if fmt_label == "HWPX" else "docx"
version = 1
if doc_type == "교육결과보고서":
    version = st.number_input("차수 (_N차)", min_value=1, value=1, step=1, key=f"doc{doc_id}_version")

if st.button("📤 출력 파일 생성"):
    try:
        outputs, photo_warnings = render_document(
            doc_type, field_data, fmt, version=version, photo_files=photo_files,
        )
    except Exception as exc:
        st.error(f"생성에 실패했습니다: {exc}")
    else:
        for w in photo_warnings:
            st.warning(w)
        if len(outputs) == 1:
            fname, data = outputs[0]
            st.download_button(f"⬇️ {fname} 다운로드", data=data, file_name=fname, key=f"doc{doc_id}_dl")
        else:
            buf = io.BytesIO()
            used_names = {}
            with zipfile.ZipFile(buf, "w") as zf:
                for fname, data in outputs:
                    if fname in used_names:
                        used_names[fname] += 1
                        base, ext = fname.rsplit(".", 1)
                        fname = f"{base}_{used_names[fname]}.{ext}"
                    else:
                        used_names[fname] = 0
                    zf.writestr(fname, data)
            zip_name = doc_row["doc_key"].replace("/", "_") + ".zip"
            st.download_button(
                f"⬇️ {len(outputs)}개 파일 zip으로 다운로드", data=buf.getvalue(),
                file_name=zip_name, key=f"doc{doc_id}_dlzip",
            )

st.divider()
with st.expander("⚠️ 문서 삭제"):
    st.warning("삭제하면 이 문서의 데이터와 저장된 원본 파일이 모두 사라지며 되돌릴 수 없습니다.")
    confirm = st.checkbox(
        f"'{doc_row['doc_key']}' 문서를 삭제하는 것에 동의합니다.", key=f"doc{doc_id}_confirm_del",
    )
    if st.button("🗑️ 삭제", disabled=not confirm, key=f"doc{doc_id}_delete_btn"):
        source_path = models.get_document(doc_id)["source_file_path"]
        models.delete_document(doc_id)
        if source_path and os.path.exists(source_path):
            os.remove(source_path)
        photo_dir = _photo_dir(doc_row["doc_key"])
        if os.path.isdir(photo_dir):
            shutil.rmtree(photo_dir)
        for k in [state_key, photo_key]:
            st.session_state.pop(k, None)
        st.success(f"'{doc_row['doc_key']}' 문서를 삭제했습니다.")
        st.rerun()
