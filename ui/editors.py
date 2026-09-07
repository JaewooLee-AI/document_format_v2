"""engine.schema 기반으로 문서 편집 폼을 동적으로 렌더링한다."""
from datetime import datetime

import pandas as pd
import streamlit as st

from engine.schema import APPOINTMENT_LETTER_PARAGRAPH_FIELDS, TABLE_SCHEMAS


def _date_field(label, value_str, key):
    val = None
    if value_str:
        try:
            val = datetime.strptime(value_str, "%Y-%m-%d").date()
        except ValueError:
            val = None
    picked = st.date_input(label, value=val, key=key)
    return picked.isoformat() if picked else ""


def _simple_field(f, field_data, key_prefix):
    name, label, kind = f["name"], f["label"], f["kind"]
    key = f"{key_prefix}_{name}"
    if f.get("fixed"):
        st.text_input(label, value=f["fixed"], disabled=True, key=key)
        field_data[name] = f["fixed"]
        return
    current = field_data.get(name, "")
    if kind == "textarea":
        field_data[name] = st.text_area(label, value=current, key=key)
    elif kind == "date":
        field_data[name] = _date_field(label, current, key)
    elif kind == "int":
        field_data[name] = st.number_input(label, value=int(current or 0), step=1, min_value=0, key=key)
    elif kind == "select":
        options = f["options"]
        index = options.index(current) if current in options else 0
        field_data[name] = st.selectbox(label, options, index=index, key=key)
    else:
        field_data[name] = st.text_input(label, value=current, key=key)


def render_table_doc_editor(doc_type: str, field_data: dict, photo_files: dict, key_prefix: str):
    schema = TABLE_SCHEMAS[doc_type]

    st.markdown("#### 기본 정보")
    cols = st.columns(2)
    for i, f in enumerate(schema.get("simple_fields", [])):
        with cols[i % 2]:
            _simple_field(f, field_data, key_prefix)

    for cc in schema.get("composed_cells", []):
        st.markdown(f"###### {cc['label']}")
        ccols = st.columns(len(cc["fields"]))
        for i, fname in enumerate(cc["fields"]):
            with ccols[i]:
                current = field_data.get(fname, 0)
                field_data[fname] = st.number_input(
                    cc["field_labels"].get(fname, fname), value=int(current or 0),
                    min_value=0, step=1, key=f"{key_prefix}_{fname}",
                )

    for lvp in schema.get("label_value_pairs", []):
        st.markdown(f"#### {lvp['label']}")
        records = field_data.setdefault(lvp["name"], [])
        for i, record in enumerate(records):
            c1, c2 = st.columns([5, 1])
            with c1:
                record[lvp["value_field"]["name"]] = st.text_area(
                    f"{lvp['value_field']['label']} #{i + 1}",
                    value=record.get(lvp["value_field"]["name"], ""),
                    key=f"{key_prefix}_{lvp['name']}_{i}",
                )
            with c2:
                st.write("")
                if st.button("삭제", key=f"{key_prefix}_{lvp['name']}_del_{i}"):
                    records.pop(i)
                    st.rerun()
        if st.button(f"+ {lvp['label']} 추가", key=f"{key_prefix}_{lvp['name']}_add"):
            records.append({lvp["value_field"]["name"]: ""})
            st.rerun()

    for rg in schema.get("repeat_groups", []):
        st.markdown(f"#### {rg['label']}")
        columns = [c for c in rg["columns"] if c["kind"] != "auto_index"]
        records = field_data.get(rg["name"], [])
        df = pd.DataFrame(records, columns=[c["name"] for c in columns]) if columns else pd.DataFrame()
        for c in columns:
            if c["name"] not in df.columns:
                df[c["name"]] = ""
        column_config = {}
        for c in columns:
            if c["kind"] == "select":
                column_config[c["name"]] = st.column_config.SelectboxColumn(c["label"], options=c["options"])
            else:
                column_config[c["name"]] = st.column_config.TextColumn(c["label"])
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config=column_config, key=f"{key_prefix}_{rg['name']}_editor",
        )
        field_data[rg["name"]] = edited.fillna("").to_dict("records")

    for ph in schema.get("photo_slots", []):
        st.markdown(f"#### {ph['label']}")
        st.caption(f"기본 안내문구: {ph['placeholder']} (사진 미첨부 시 그대로 유지됩니다)")
        up = st.file_uploader(
            f"{ph['label']} 업로드 (선택)", type=["jpg", "jpeg", "png"], key=f"{key_prefix}_{ph['name']}_photo",
        )
        if up is not None:
            photo_files[ph["name"]] = up.getvalue()
        elif ph["name"] in photo_files and st.button(f"{ph['label']} 제거", key=f"{key_prefix}_{ph['name']}_rm"):
            del photo_files[ph["name"]]
            st.rerun()


def render_appointment_editor(field_data: dict, key_prefix: str):
    st.markdown("#### 공통")
    field_data["발행일"] = _date_field("발행일", field_data.get("발행일", ""), f"{key_prefix}_issue_date")

    st.markdown("#### 위원 목록 (1인당 1장 생성)")
    members = field_data.setdefault("위원목록", [])
    for i, member in enumerate(members):
        with st.container(border=True):
            st.markdown(f"**위원 {i + 1}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                member["위원소속"] = st.text_input("위원 소속", value=member.get("위원소속", ""), key=f"{key_prefix}_m{i}_aff")
            with c2:
                member["위원직위"] = st.text_input("위원 직위", value=member.get("위원직위", ""), key=f"{key_prefix}_m{i}_pos")
            with c3:
                member["위원성명"] = st.text_input("위원 성명", value=member.get("위원성명", ""), key=f"{key_prefix}_m{i}_name")
            c4, c5, c6 = st.columns(3)
            with c4:
                member["위촉시작일"] = _date_field("위촉 시작일", member.get("위촉시작일", ""), f"{key_prefix}_m{i}_start")
            with c5:
                member["위촉종료일"] = _date_field("위촉 종료일", member.get("위촉종료일", ""), f"{key_prefix}_m{i}_end")
            with c6:
                member["문서번호"] = st.text_input("문서번호 (선택)", value=member.get("문서번호", ""), key=f"{key_prefix}_m{i}_docno")
            if st.button("이 위원 삭제", key=f"{key_prefix}_m{i}_del"):
                members.pop(i)
                st.rerun()
    if st.button("+ 위원 추가", key=f"{key_prefix}_add_member"):
        members.append({k["name"]: "" for k in APPOINTMENT_LETTER_PARAGRAPH_FIELDS if k["name"] != "발행일"})
        st.rerun()
