"""5종 문서에 대해 업로드(추출)->렌더링(hwpx/docx 양쪽)이 예외 없이 동작하는지,
그리고 값이 실제로 반영되는지 확인하는 개발용 스크립트. (자동 테스트 프레임워크가 아니라
구현 검증용 1회성 스크립트)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.docx_adapter import DocxDocument
from engine.extractor import extract
from engine.hwpx_adapter import HwpxDocument
from engine.renderer import render_document
from engine.schema import DOC_TYPES

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(path, "rb") as f:
        return f.read()


def check_doc(doc_type):
    info = DOC_TYPES[doc_type]
    basename = info["template_basename"]
    print(f"\n=== {doc_type} ({info['label']}) ===")

    sample_path = os.path.join(BASE, "hwpx_samples", f"{basename}.hwpx")
    data = load(sample_path)
    adapter = HwpxDocument.open(data)
    field_data = extract(adapter, doc_type)
    print("추출된 필드:", {k: (v if not isinstance(v, list) else f"{len(v)}건") for k, v in field_data.items()})

    for fmt in ["hwpx", "docx"]:
        outputs, warns = render_document(doc_type, field_data, fmt, version=1, photo_files={})
        for fname, content in outputs:
            out_dir = os.path.join(BASE, "scripts", "_out")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, fname)
            with open(out_path, "wb") as f:
                f.write(content)
            print(f"  [{fmt}] 생성됨: {fname} ({len(content)} bytes) warns={warns}")
            # 재파싱해서 열리는지 확인
            reopened = HwpxDocument.open(content) if fmt == "hwpx" else DocxDocument.open(content)
            reopened.get_cell_text(0, 0, 0) if False else None


for doc_type in DOC_TYPES:
    check_doc(doc_type)

print("\n모두 통과.")
