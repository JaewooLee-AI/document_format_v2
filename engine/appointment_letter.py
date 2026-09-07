"""사회적 성과 평가위원 위촉장 전용 처리.

이 문서는 표가 아니라 하나의 표 셀(table=0, row=0, col=0) 안에 있는 10개 문단의
"빈칸 채우기" 텍스트로 구성되어 있다(hwpx_forms/docx_forms 실물 확인, 두 포맷 모두
문단/런 구성이 동일함). 문단·런 인덱스는 고정이므로 좌표를 하드코딩한다.

문단 구성(0-based):
  0: 제 20 －    호            (문서번호, 선택)
  1: 위    촉    장             (고정 제목, 건드리지 않음)
  2: 소 속 : ______            (위원 소속)
  3: 직 위 : ______            (위원 직위)
  4: 성 명 : ______            (위원 성명)
  5: 귀하를 20 년 월 일부터 20 년 월 일까지   (위촉기간)
  6: (주)＿＿＿＿＿의 / 사회적 성과 평가위원 / 으로 위촉합니다.   (run0만 기업명 고정값)
  7: 20 년 월 일                (발행일)
  8: (주) ＿ ＿ ＿ ＿ ＿          (기업명 고정값)
  9: 대  표    ＿ ＿ ＿   (인)    (대표 고정값)
"""
import re

COMPANY_NAME = "더느린걸음"
REPRESENTATIVE_NAME = "장진수"

TABLE, ROW, COL = 0, 0, 0


def _strip_blank(s: str) -> str:
    return s.strip(" \t_＿")


def _format_date_ymd(date_str: str):
    """'YYYY-MM-DD' -> (년, 월, 일) 문자열 튜플. 파싱 실패 시 (None, None, None)."""
    if not date_str:
        return None, None, None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_str.strip())
    if not m:
        return None, None, None
    y, mo, d = m.groups()
    return y, str(int(mo)), str(int(d))


def render(adapter, field_data: dict):
    """field_data 의 값으로 위촉장 문단들을 다시 작성한다."""
    doc_no = (field_data.get("문서번호") or "").strip()
    if doc_no:
        adapter.set_paragraph_run_text(TABLE, ROW, COL, 0, 0, f"제 20 － {doc_no} 호")
    # 문서번호 미입력 시 원본 빈칸 유지(건드리지 않음)

    affiliation = field_data.get("위원소속") or ""
    adapter.set_paragraph_run_text(TABLE, ROW, COL, 2, 0, f"소 속 : {affiliation}")

    position = field_data.get("위원직위") or ""
    adapter.set_paragraph_run_text(TABLE, ROW, COL, 3, 0, f"직 위 : {position}")

    name = field_data.get("위원성명") or ""
    adapter.set_paragraph_run_text(TABLE, ROW, COL, 4, 0, f"성 명 : {name}")

    sy, sm, sd = _format_date_ymd(field_data.get("위촉시작일"))
    ey, em, ed = _format_date_ymd(field_data.get("위촉종료일"))
    if sy and ey:
        adapter.set_paragraph_run_text(
            TABLE, ROW, COL, 5, 0,
            f"귀하를 {sy}  년  {sm} 월 {sd}  일부터 {ey}  년  {em} 월 {ed}  일까지",
        )

    adapter.set_paragraph_run_text(TABLE, ROW, COL, 6, 0, f"(주){COMPANY_NAME}의 ")

    iy, im, id_ = _format_date_ymd(field_data.get("발행일"))
    if iy:
        adapter.set_paragraph_run_text(TABLE, ROW, COL, 7, 0, f"{iy}  년  {im} 월 {id_}  일")

    adapter.set_paragraph_run_text(TABLE, ROW, COL, 8, 0, f"(주) {COMPANY_NAME}")
    adapter.set_paragraph_run_text(TABLE, ROW, COL, 9, 0, f"대  표    {REPRESENTATIVE_NAME}   (인)")


def extract_best_effort(adapter) -> dict:
    """업로드된 샘플에서 값을 베스트에포트로 추출한다(실패 시 빈 값)."""
    data = {}
    try:
        p0 = adapter.get_paragraph_run_text(TABLE, ROW, COL, 0, 0)
        m = re.match(r"^제\s*20\s*－\s*(.*?)\s*호$", p0)
        data["문서번호"] = m.group(1) if m and m.group(1) else ""
    except Exception:
        data["문서번호"] = ""

    for name, idx, prefix in [("위원소속", 2, "소"), ("위원직위", 3, "직"), ("위원성명", 4, "성")]:
        try:
            text = adapter.get_paragraph_run_text(TABLE, ROW, COL, idx, 0)
            value = re.sub(r"^[가-힣]\s*[가-힣]?\s*:\s*", "", text)
            data[name] = _strip_blank(value)
        except Exception:
            data[name] = ""

    try:
        p5 = adapter.get_paragraph_run_text(TABLE, ROW, COL, 5, 0)
        dates = re.findall(r"(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일", p5)
        dates = [(y, m, d) for (y, m, d) in dates if int(y) >= 1900]
        if len(dates) >= 2:
            y, m, d = dates[0]
            data["위촉시작일"] = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            y, m, d = dates[1]
            data["위촉종료일"] = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        else:
            data["위촉시작일"] = ""
            data["위촉종료일"] = ""
    except Exception:
        data["위촉시작일"] = ""
        data["위촉종료일"] = ""

    try:
        p7 = adapter.get_paragraph_run_text(TABLE, ROW, COL, 7, 0)
        m = re.search(r"(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일", p7)
        if m and int(m.group(1)) >= 1900:
            y, mo, d = m.groups()
            data["발행일"] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        else:
            data["발행일"] = ""
    except Exception:
        data["발행일"] = ""

    return data
