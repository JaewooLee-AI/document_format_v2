"""업로드된 파일의 전체 텍스트를 훑어 5종 문서 중 어떤 업무 종류인지 자동으로 추정한다.

각 hwpx_forms/docx_forms 원본의 제목 문단이 DOC_TYPES 의 label과 정확히 일치하는 것을
확인했다(예: '평가위원회 회의록'). 다만 위촉장은 제목이 '위    촉    장'(공백 포함)으로
label 전체와 일치하지 않아 '위촉'이라는 고유 키워드로 별도 판별한다. 다른 4종 문서에는
'위촉'이라는 단어가 전혀 등장하지 않아 안전하게 구분된다.
"""
import io
import zipfile
import xml.etree.ElementTree as ET

from engine.hwpx_adapter import HP
from engine.schema import DOC_TYPES


def _hwpx_full_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        section0 = zf.read("Contents/section0.xml")
    root = ET.fromstring(section0)
    return "".join(t.text or "" for t in root.iter(HP + "t"))


def _docx_full_text(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return " ".join(parts)


def classify_document(data: bytes, ext: str) -> str:
    """감지된 doc_type 키를 반환한다. 판별 실패 시 None."""
    try:
        text = _hwpx_full_text(data) if ext == "hwpx" else _docx_full_text(data)
    except Exception:
        return None

    if "위촉" in text:
        return "위촉장"
    for doc_type, info in DOC_TYPES.items():
        if doc_type == "위촉장":
            continue
        if info["label"] in text:
            return doc_type
    return None
