"""SVI_forms.md 5장 파일명 규칙.

- 기본: SVI_문서명_YYYYMMDD.{ext}
- 교육 결과 보고서: SVI_교육결과보고서_YYYYMMDD_교육명_N차
- 협력활동 보고서: SVI_협력활동보고서_YYYYMMDD_협력기관
- 날짜는 실시일 기준(괄호 미사용), 버전은 _N차 로만 표기.
"""
import re

DOC_NAME_FOR_FILENAME = {
    "성과관리보고서": "사회적성과관리보고서",
    "회의록": "평가위원회회의록",
    "위촉장": "사회적성과평가위원위촉장",
    "교육결과보고서": "교육결과보고서",
    "협력활동보고서": "협력활동보고서",
}


def _sanitize(text: str) -> str:
    text = (text or "").strip()
    text = text.replace("(", "").replace(")", "")
    text = re.sub(r"\s+", "", text)
    return text


def _yyyymmdd(date_str: str, fallback: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str or "")
    if m:
        return "".join(m.groups())
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", fallback or "")
    if m:
        return "".join(m.groups())
    return "00000000"


def build_filename(doc_type: str, field_data: dict, ext: str, version: int = 1) -> str:
    name = DOC_NAME_FOR_FILENAME[doc_type]
    ext = ext.lstrip(".")

    if doc_type == "교육결과보고서":
        date = _yyyymmdd(_first_date_in_range(field_data.get("교육기간")), "")
        course = _sanitize(field_data.get("교육명"))
        return f"SVI_{name}_{date}_{course}_{version}차.{ext}"

    if doc_type == "협력활동보고서":
        date = _yyyymmdd(field_data.get("작성일자"), "")
        partners = []
        for r in field_data.get("협력내용요약", []) or []:
            if r.get("협력기관"):
                partners.append(_sanitize(r["협력기관"]))
        partner = partners[0] if partners else ""
        return f"SVI_{name}_{date}_{partner}.{ext}"

    if doc_type == "위촉장":
        date = _yyyymmdd(field_data.get("발행일"), "")
        member_name = _sanitize(field_data.get("위원성명"))
        suffix = f"_{member_name}" if member_name else ""
        return f"SVI_{name}_{date}{suffix}.{ext}"

    date = _yyyymmdd(field_data.get("작성일자"), "")
    return f"SVI_{name}_{date}.{ext}"


def _first_date_in_range(range_str: str) -> str:
    """'2026-01-01~2026-01-02' 또는 '2026.01.01~01.02' 같은 문자열에서 시작일을 뽑는다."""
    if not range_str:
        return ""
    m = re.search(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", range_str)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"
