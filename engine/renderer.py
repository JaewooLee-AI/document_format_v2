"""field_data(JSON) + doc_type + 출력 포맷 -> 실제 hwpx/docx 파일 바이트.

항상 hwpx_forms/ 또는 docx_forms/ 안의 '빈 양식'을 열어 값을 주입하는 방식으로 생성한다
(원본 업로드 파일을 직접 변환하지 않음). 이렇게 하면 SVI_forms.md 서식 규격(폰트·테두리 등)이
항상 그대로 보장된다.
"""
import os

from engine import appointment_letter, filenames, photos
from engine import schema as sch
from engine.docx_adapter import DocxDocument
from engine.hwpx_adapter import HwpxDocument

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HWPX_FORMS_DIR = os.path.join(BASE_DIR, "hwpx_forms")
DOCX_FORMS_DIR = os.path.join(BASE_DIR, "docx_forms")


def _load_template_bytes(doc_type: str, fmt: str) -> bytes:
    basename = sch.DOC_TYPES[doc_type]["template_basename"]
    folder = HWPX_FORMS_DIR if fmt == "hwpx" else DOCX_FORMS_DIR
    ext = "hwpx" if fmt == "hwpx" else "docx"
    path = os.path.join(folder, f"{basename}.{ext}")
    with open(path, "rb") as f:
        return f.read()


def _open_adapter(fmt: str, data: bytes):
    return HwpxDocument.open(data) if fmt == "hwpx" else DocxDocument.open(data)


def _format_value(value, kind: str) -> str:
    if value is None:
        return ""
    if kind == "date":
        parts = str(value).split("-")
        return ".".join(parts) if len(parts) == 3 else str(value)
    if kind == "int":
        return str(value)
    return str(value)


def render_document(doc_type: str, field_data: dict, fmt: str, version: int = 1, photo_files: dict = None):
    """반환값: [(filename, bytes), ...]. 위촉장은 위원 1인당 1개 파일을 반환한다."""
    photo_files = photo_files or {}
    template_bytes = _load_template_bytes(doc_type, fmt)
    ext = "hwpx" if fmt == "hwpx" else "docx"

    if doc_type == "위촉장":
        outputs = []
        members = field_data.get("위원목록") or [{}]
        for member in members:
            adapter = _open_adapter(fmt, template_bytes)
            data = dict(member)
            data["발행일"] = field_data.get("발행일")
            appointment_letter.render(adapter, data)
            fname = filenames.build_filename(doc_type, data, ext, version)
            outputs.append((fname, adapter.to_bytes()))
        return outputs, []

    schema = sch.TABLE_SCHEMAS[doc_type]
    adapter = _open_adapter(fmt, template_bytes)

    for f in schema.get("simple_fields", []):
        value = field_data.get(f["name"], f.get("fixed", ""))
        adapter.set_cell_text(f["table"], f["row"], f["col"], _format_value(value, f["kind"]))

    for cc in schema.get("composed_cells", []):
        values = {k: field_data.get(k, 0) for k in cc["fields"]}
        adapter.set_cell_text(cc["table"], cc["row"], cc["col"], cc["template"].format(**values))

    for lvp in schema.get("label_value_pairs", []):
        records = field_data.get(lvp["name"], []) or []
        n = max(len(records), 1)
        adapter.set_pair_count(lvp["table"], n)
        for i in range(n):
            record = records[i] if i < len(records) else {}
            adapter.set_cell_text(lvp["table"], 2 * i + 1, lvp["col"], record.get(lvp["value_field"]["name"], ""))

    for rg in schema.get("repeat_groups", []):
        records = field_data.get(rg["name"], []) or []
        n = max(len(records), 1)
        adapter.ensure_row_count(rg["table"], rg["header_row"], n)
        for i in range(n):
            record = records[i] if i < len(records) else {}
            for col in rg["columns"]:
                text = str(i + 1) if col["kind"] == "auto_index" else record.get(col["name"], "")
                adapter.set_cell_text(rg["table"], rg["header_row"] + 1 + i, col["col"], text)

    photo_warnings = []
    for ph in schema.get("photo_slots", []):
        img_bytes = photo_files.get(ph["name"])
        if not img_bytes:
            continue
        try:
            if fmt == "docx":
                photos.insert_into_docx(adapter, ph["table"], ph["row"], ph["col"], img_bytes)
            else:
                photos.insert_into_hwpx(adapter, ph["table"], ph["row"], ph["col"], img_bytes)
        except Exception as exc:  # best-effort: 실패해도 문서 전체는 안내문구 유지한 채 살아있게
            photo_warnings.append(f"{ph['label']} 삽입 실패({fmt}): {exc}")

    fname = filenames.build_filename(doc_type, field_data, ext, version)
    return [(fname, adapter.to_bytes())], photo_warnings
