"""업로드된 hwpx/docx 파일에서 engine.schema 기준으로 field_data(JSON) 를 추출한다."""
import re

from engine import appointment_letter
from engine.schema import TABLE_SCHEMAS


def extract(adapter, doc_type: str) -> dict:
    if doc_type == "위촉장":
        member = appointment_letter.extract_best_effort(adapter)
        issue_date = member.pop("발행일", "")
        return {"발행일": issue_date, "위원목록": [member]}

    schema = TABLE_SCHEMAS[doc_type]
    data = {}

    for f in schema.get("simple_fields", []):
        if f.get("fixed"):
            data[f["name"]] = f["fixed"]
            continue
        text = adapter.get_cell_text(f["table"], f["row"], f["col"])
        data[f["name"]] = _parse_value(text, f["kind"])

    for cc in schema.get("composed_cells", []):
        text = adapter.get_cell_text(cc["table"], cc["row"], cc["col"])
        nums = re.findall(r"\d+", text)
        for i, name in enumerate(cc["fields"]):
            data[name] = int(nums[i]) if i < len(nums) else 0

    for lvp in schema.get("label_value_pairs", []):
        pairs = adapter.get_pair_count(lvp["table"])
        records = []
        for i in range(pairs):
            value_row = 2 * i + 1
            text = adapter.get_cell_text(lvp["table"], value_row, lvp["col"])
            records.append({lvp["value_field"]["name"]: text})
        data[lvp["name"]] = records

    for rg in schema.get("repeat_groups", []):
        n = adapter.get_row_count(rg["table"], rg["header_row"])
        records = []
        for r in range(n):
            row = {}
            for col in rg["columns"]:
                if col["kind"] == "auto_index":
                    continue
                text = adapter.get_cell_text(rg["table"], rg["header_row"] + 1 + r, col["col"])
                row[col["name"]] = text
            records.append(row)
        data[rg["name"]] = records

    return data


def _parse_value(text: str, kind: str):
    text = (text or "").strip()
    if kind == "int":
        m = re.search(r"\d+", text)
        return int(m.group()) if m else 0
    if kind == "date":
        m = re.match(r"^(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", text)
        if m:
            y, mo, d = m.groups()
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        return ""
    return text
