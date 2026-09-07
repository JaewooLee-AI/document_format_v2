"""사진 삽입 (SVI_forms.md 4장 사진칸 규격).

- EXIF Orientation 을 픽셀에 반영한 뒤 삽입한다 (Word/LibreOffice 는 EXIF 회전 태그를 무시함).
- 높이를 4.00cm 로 고정하고 폭은 원본 비율로 계산한다.
- DOCX 는 python-docx 로 안정적으로 구현한다.
- HWPX 는 hp:pic XML을 직접 생성하는 베스트에포트 구현이다. 참고할 기존 삽입 예시가 없어
  실제 한글 프로그램에서 열어 검증이 필요하다 — 문제가 있으면 예외를 던지도록 하고,
  호출부(engine.renderer)에서 실패해도 문서 전체가 깨지지 않도록 원본 안내문구를 유지한다.
"""
import io
import uuid
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps

TARGET_HEIGHT_CM = 4.00
HWPUNIT_PER_CM = 7200 / 2.54  # 1 inch = 7200 HWPUNIT


def normalize_image(image_bytes: bytes) -> tuple[bytes, int, int]:
    """EXIF 회전을 픽셀에 반영하고 JPEG로 재인코딩한다. (jpeg_bytes, width_px, height_px) 반환."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue(), img.width, img.height


def insert_into_docx(docx_adapter, table_index, row, col, image_bytes: bytes):
    jpeg_bytes, _, _ = normalize_image(image_bytes)
    docx_adapter.insert_image(table_index, row, col, io.BytesIO(jpeg_bytes), TARGET_HEIGHT_CM)


def insert_into_hwpx(hwpx_adapter, table_index, row, col, image_bytes: bytes):
    """베스트에포트 구현. 실패 시 예외를 던진다(호출부에서 catch하여 안내문구를 유지)."""
    from engine.hwpx_adapter import HP

    jpeg_bytes, px_w, px_h = normalize_image(image_bytes)
    height_cm = TARGET_HEIGHT_CM
    width_cm = height_cm * (px_w / px_h)
    cur_w = round(width_cm * HWPUNIT_PER_CM)
    cur_h = round(height_cm * HWPUNIT_PER_CM)

    bin_id = f"img_{uuid.uuid4().hex[:12]}"
    bin_filename = f"BinData/{bin_id}.jpg"
    hwpx_adapter.add_binary(bin_filename, jpeg_bytes, bin_id)

    tc = hwpx_adapter._cell(table_index, row, col)
    sublist = tc.find(HP + "subList")
    ps = list(sublist.findall(HP + "p"))
    template_p = ps[0]
    for p in ps:
        sublist.remove(p)

    new_p = ET.Element(HP + "p", {"id": "0", "paraPrIDRef": template_p.get("paraPrIDRef", "0"),
                                   "styleIDRef": "0", "pageBreak": "0", "columnBreak": "0", "merged": "0"})
    run = ET.SubElement(new_p, HP + "run", {"charPrIDRef": "0"})
    pic = ET.SubElement(run, HP + "pic", {
        "id": "0", "reverse": "0", "groupLevel": "0", "numberingType": "PICTURE",
        "textWrap": "TOP_AND_BOTTOM", "textFlow": "BOTH_SIDES", "lock": "0",
        "dropcapstyle": "None", "pageBreak": "CELL",
    })
    ET.SubElement(pic, HP + "pos", {
        "treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1", "allowOverlap": "0",
        "vertRelTo": "PARA", "horzRelTo": "COLUMN", "vertAlign": "TOP", "horzAlign": "LEFT",
        "vertOffset": "0", "horzOffset": "0",
    })
    ET.SubElement(pic, HP + "sz", {
        "width": str(cur_w), "widthRelTo": "ABSOLUTE", "height": str(cur_h),
        "heightRelTo": "ABSOLUTE", "protect": "0",
    })
    ET.SubElement(pic, HP + "outMargin", {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    ET.SubElement(pic, HP + "imgRect")
    ET.SubElement(pic, HP + "imgClip", {"left": "0", "right": str(px_w), "top": "0", "bottom": str(px_h)})
    ET.SubElement(pic, HP + "inMargin", {"left": "0", "right": "0", "top": "0", "bottom": "0"})
    ET.SubElement(pic, HP + "imgDim", {"dpi": "96", "dpiY": "96"})
    ET.SubElement(pic, HP + "img", {"binaryItemIDRef": bin_id, "bright": "0", "contrast": "0",
                                     "effect": "REAL_PIC", "alpha": "0"})
    sublist.append(new_p)
