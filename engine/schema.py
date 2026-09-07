"""
5종 SVI 제출서류의 필드 스키마.

hwpx_forms/*.hwpx 와 docx_forms/*.docx 를 직접 열어 표 구조(표 순서, 행/열 좌표, 라벨 문구)가
두 포맷에서 완전히 동일함을 확인했다. 따라서 이 스키마는 포맷과 무관한 논리 좌표
(table 순번, row, col — 모두 0-based)만 정의하고, 실제 셀 접근은 engine.hwpx_adapter /
engine.docx_adapter 가 각자의 방식으로 구현한다.

주의: SVI_forms.md의 서술(예: 회의록의 "위원명 | 의견" 2열 표, 협력활동 보고서의
"일자|활동내용|참여인원|장소" 표)과 실제 배포된 hwpx_forms/docx_forms 파일의 구조가
다른 부분이 있다. 이 스키마는 실제로 채워 넣어야 하는 파일(hwpx_forms/docx_forms)의
"진짜" 구조를 기준으로 만들었다 — 출력은 결국 이 파일들에 값을 주입하는 방식이기 때문이다.
"""

DOC_TYPES = {
    "성과관리보고서": {
        "label": "사회적 성과관리 보고서",
        "template_basename": "사회적 성과관리 보고서",
        "indicator": "지표 2",
    },
    "회의록": {
        "label": "평가위원회 회의록",
        "template_basename": "평가위원회 회의록",
        "indicator": "지표 2",
    },
    "위촉장": {
        "label": "사회적 성과 평가위원 위촉장",
        "template_basename": "사회적 성과 평가위원 위촉장",
        "indicator": "지표 2",
    },
    "교육결과보고서": {
        "label": "교육 결과 보고서",
        "template_basename": "교육 결과 보고서",
        "indicator": "지표 9",
    },
    "협력활동보고서": {
        "label": "협력활동 보고서",
        "template_basename": "협력활동 보고서",
        "indicator": "지표 4·5",
    },
}

EDUCATION_METHODS = ["내부교육(집합)", "내부교육(온라인)", "외부교육(집합)", "외부교육(온라인)"]
COOPERATION_TYPES = ["지역사회 협력", "기관 간 협력", "기타"]
MEMBER_TYPES = ["사내", "사외"]

# ---------------------------------------------------------------------------
# 회의록
# ---------------------------------------------------------------------------
MEETING_MINUTES_SCHEMA = {
    "simple_fields": [
        {"name": "기업명", "label": "기업명", "table": 0, "row": 0, "col": 1, "kind": "text", "fixed": "주식회사 더느린걸음"},
        {"name": "작성일자", "label": "작성일자", "table": 0, "row": 0, "col": 3, "kind": "date"},
        {"name": "회의명", "label": "회의명(안건)", "table": 0, "row": 1, "col": 1, "kind": "text"},
        {"name": "회의일자", "label": "회의일자", "table": 0, "row": 1, "col": 3, "kind": "date"},
        {"name": "장소", "label": "장소", "table": 0, "row": 2, "col": 1, "kind": "text"},
        {"name": "비고", "label": "비고(기타의견)", "table": 2, "row": 0, "col": 0, "kind": "textarea"},
    ],
    # 참석 위원 수 3개 필드가 실제로는 표0 (row=3,col=1) 한 셀에
    # "총 N명 (내부 N명 / 외부 N명)" 형태 문자열로 합쳐져 들어간다.
    "composed_cells": [
        {
            "table": 0, "row": 3, "col": 1,
            "label": "참석 위원 수",
            "template": "총 {참석위원_총원}명 (내부 {참석위원_내부}명 / 외부 {참석위원_외부}명)",
            "fields": ["참석위원_총원", "참석위원_내부", "참석위원_외부"],
            "field_labels": {"참석위원_총원": "총원", "참석위원_내부": "내부", "참석위원_외부": "외부"},
        }
    ],
    # 위원별 의견: 표1은 라벨행("위원명")+값행이 번갈아 반복되는 1열 표.
    # 값 칸 하나에 위원명+의견을 자유 텍스트로 함께 적는다(실제 양식 구조).
    "label_value_pairs": [
        {
            "name": "위원의견",
            "label": "평가의견 (위원별)",
            "table": 1,
            "col": 0,
            "label_text": "위원명",
            "value_field": {"name": "내용", "label": "위원명 및 의견", "kind": "textarea"},
            "template_pair_count": 2,
        }
    ],
    "photo_slots": [
        {"name": "회의사진", "label": "사진 첨부란", "table": 3, "row": 0, "col": 0,
         "placeholder": "(회의 진행 사진 또는 관련 자료 사진 삽입)"},
    ],
}

# ---------------------------------------------------------------------------
# 교육 결과 보고서
# ---------------------------------------------------------------------------
EDUCATION_REPORT_SCHEMA = {
    "simple_fields": [
        {"name": "기업명", "label": "기업명", "table": 0, "row": 0, "col": 1, "kind": "text", "fixed": "주식회사 더느린걸음"},
        {"name": "보고자", "label": "보고자", "table": 0, "row": 0, "col": 3, "kind": "text"},
        {"name": "교육명", "label": "교육명", "table": 0, "row": 1, "col": 1, "kind": "text"},
        {"name": "교육기관", "label": "교육기관", "table": 0, "row": 2, "col": 1, "kind": "text"},
        {"name": "교육방식", "label": "교육방식", "table": 0, "row": 2, "col": 3, "kind": "select", "options": EDUCATION_METHODS},
        {"name": "교육기간", "label": "교육기간", "table": 0, "row": 3, "col": 1, "kind": "text"},
        {"name": "총교육시간", "label": "총 교육시간", "table": 0, "row": 3, "col": 3, "kind": "text"},
        {"name": "강사", "label": "강사", "table": 0, "row": 4, "col": 1, "kind": "text"},
        {"name": "장소", "label": "장소", "table": 0, "row": 4, "col": 3, "kind": "text"},
        {"name": "참석인원", "label": "참석인원", "table": 0, "row": 5, "col": 1, "kind": "int"},
        {"name": "주요교육내용", "label": "주요 교육내용 (개조식 3~5개)", "table": 0, "row": 6, "col": 1, "kind": "textarea"},
        {"name": "비고", "label": "비고", "table": 0, "row": 8, "col": 1, "kind": "textarea"},
    ],
    "photo_slots": [
        {"name": "교육사진", "label": "사진", "table": 0, "row": 7, "col": 1,
         "placeholder": "(교육 진행 또는 교육자료 사진 삽입)"},
    ],
    "repeat_groups": [
        {
            "name": "참석자명단", "label": "참석자 명단", "table": 1,
            "header_row": 0, "template_row_count": 5,
            "columns": [
                {"name": "연번", "label": "연번", "col": 0, "kind": "auto_index"},
                {"name": "성명", "label": "성명", "col": 1, "kind": "text"},
                {"name": "서명", "label": "서명", "col": 2, "kind": "text", "note": "빈칸 출력 후 수기 서명"},
            ],
        }
    ],
}

# ---------------------------------------------------------------------------
# 협력활동 보고서 (상세 블록이 최대 2개 슬롯으로 고정된 실제 양식 구조)
# ---------------------------------------------------------------------------
def _cooperation_detail_fields(slot_index, table_index):
    prefix = f"상세{slot_index}_"
    return [
        {"name": f"{prefix}협력기관명", "label": "협력기관명", "table": table_index, "row": 0, "col": 1, "kind": "text"},
        {"name": f"{prefix}목적", "label": "목적", "table": table_index, "row": 1, "col": 1, "kind": "textarea"},
        {"name": f"{prefix}협력활동내용", "label": "협력활동 내용", "table": table_index, "row": 2, "col": 1, "kind": "textarea"},
        {"name": f"{prefix}일시장소", "label": "일시 / 장소", "table": table_index, "row": 3, "col": 1, "kind": "text"},
        {"name": f"{prefix}대상", "label": "대상", "table": table_index, "row": 4, "col": 1, "kind": "text"},
        {"name": f"{prefix}비용역할분담", "label": "비용 / 역할분담", "table": table_index, "row": 5, "col": 1, "kind": "textarea"},
        {"name": f"{prefix}목적달성여부", "label": "목적달성 여부", "table": table_index, "row": 6, "col": 1, "kind": "textarea"},
    ]


COOPERATION_REPORT_SCHEMA = {
    "simple_fields": [
        {"name": "기업명", "label": "기업명", "table": 0, "row": 0, "col": 1, "kind": "text", "fixed": "주식회사 더느린걸음"},
        {"name": "작성일자", "label": "작성일자", "table": 0, "row": 0, "col": 3, "kind": "date"},
        {"name": "담당자", "label": "담당자(직책)", "table": 0, "row": 1, "col": 1, "kind": "text"},
        {"name": "협력유형", "label": "협력 유형", "table": 0, "row": 1, "col": 3, "kind": "select", "options": COOPERATION_TYPES},
        *_cooperation_detail_fields(1, 2),
        *_cooperation_detail_fields(2, 3),
    ],
    "photo_slots": [
        {"name": "상세1_활동사진", "label": "협력활동 사진 (상세1)", "table": 2, "row": 7, "col": 1,
         "placeholder": "(협력활동 사진 삽입)"},
        {"name": "상세2_활동사진", "label": "협력활동 사진 (상세2)", "table": 3, "row": 7, "col": 1,
         "placeholder": "(협력활동 사진 삽입)"},
    ],
    "repeat_groups": [
        {
            "name": "협력내용요약", "label": "협력 내용 요약", "table": 1,
            "header_row": 0, "template_row_count": 2,
            "columns": [
                {"name": "연번", "label": "연번", "col": 0, "kind": "auto_index"},
                {"name": "협력기관", "label": "협력기관", "col": 1, "kind": "text"},
                {"name": "협력활동", "label": "협력활동", "col": 2, "kind": "text"},
                {"name": "횟수", "label": "횟수", "col": 3, "kind": "text"},
            ],
        }
    ],
}

# ---------------------------------------------------------------------------
# 사회적 성과관리 보고서
# ---------------------------------------------------------------------------
PERFORMANCE_REPORT_SCHEMA = {
    "simple_fields": [
        {"name": "기업명", "label": "기업명", "table": 0, "row": 0, "col": 1, "kind": "text", "fixed": "주식회사 더느린걸음"},
        {"name": "작성일자", "label": "작성일자", "table": 0, "row": 0, "col": 3, "kind": "date"},
        {"name": "담당부서", "label": "담당부서", "table": 0, "row": 1, "col": 1, "kind": "text"},
        {"name": "담당자", "label": "담당자(직책)", "table": 0, "row": 1, "col": 3, "kind": "text"},
    ],
    "repeat_groups": [
        {
            "name": "측정기준", "label": "① 측정기준", "table": 1,
            "header_row": 0, "template_row_count": 2,
            "columns": [
                {"name": "목표", "label": "목표", "col": 0, "kind": "text"},
                {"name": "지표", "label": "지표(세부목표)", "col": 1, "kind": "text"},
                {"name": "S", "label": "S", "col": 2, "kind": "text"},
                {"name": "A", "label": "A", "col": 3, "kind": "text"},
                {"name": "B", "label": "B", "col": 4, "kind": "text"},
                {"name": "C", "label": "C", "col": 5, "kind": "text"},
                {"name": "D", "label": "D", "col": 6, "kind": "text"},
            ],
        },
        {
            "name": "성과보고", "label": "② 성과보고", "table": 2,
            "header_row": 0, "template_row_count": 2,
            "columns": [
                {"name": "목표", "label": "목표", "col": 0, "kind": "text"},
                {"name": "지표", "label": "지표(세부목표)", "col": 1, "kind": "text"},
                {"name": "실적", "label": "추진 활동내용 및 실적", "col": 2, "kind": "text"},
                {"name": "결과", "label": "결과", "col": 3, "kind": "text"},
                {"name": "등급", "label": "등급", "col": 4, "kind": "select", "options": ["S", "A", "B", "C", "D"]},
            ],
        },
        {
            "name": "평가위원명단", "label": "③ 평가위원 명단", "table": 3,
            "header_row": 0, "template_row_count": 3,
            "columns": [
                {"name": "연번", "label": "연번", "col": 0, "kind": "auto_index"},
                {"name": "위원명", "label": "위원명", "col": 1, "kind": "text"},
                {"name": "소속", "label": "소속", "col": 2, "kind": "text"},
                {"name": "구분", "label": "구분(사내/사외)", "col": 3, "kind": "select", "options": MEMBER_TYPES},
            ],
        },
    ],
}

TABLE_SCHEMAS = {
    "회의록": MEETING_MINUTES_SCHEMA,
    "교육결과보고서": EDUCATION_REPORT_SCHEMA,
    "협력활동보고서": COOPERATION_REPORT_SCHEMA,
    "성과관리보고서": PERFORMANCE_REPORT_SCHEMA,
}

# ---------------------------------------------------------------------------
# 위촉장: 표가 아니라 하나의 셀 안 문단(run)에 대한 빈칸 채우기 구조.
# engine/appointment_letter.py 에서 이 스펙을 사용한다.
# 좌표는 (table=0, row=0, col=0) 셀 안의 paragraph_index / run_index.
# ---------------------------------------------------------------------------
APPOINTMENT_LETTER_PARAGRAPH_FIELDS = [
    {"name": "문서번호", "label": "문서번호", "paragraph": 0, "run": 0, "kind": "text", "required": False},
    {"name": "위원소속", "label": "위원 소속", "paragraph": 2, "run": 0, "kind": "text", "required": True},
    {"name": "위원직위", "label": "위원 직위", "paragraph": 3, "run": 0, "kind": "text", "required": True},
    {"name": "위원성명", "label": "위원 성명", "paragraph": 4, "run": 0, "kind": "text", "required": True},
    {"name": "위촉시작일", "label": "위촉 시작일", "paragraph": 5, "run": 0, "kind": "date", "required": True},
    {"name": "위촉종료일", "label": "위촉 종료일", "paragraph": 5, "run": 0, "kind": "date", "required": True},
    {"name": "발행일", "label": "발행일", "paragraph": 7, "run": 0, "kind": "date", "required": True},
]
