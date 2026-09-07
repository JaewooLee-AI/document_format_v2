"""SVI_forms.md '요건' 항목에 대한 soft validation. 저장/출력을 막지 않고 경고 메시지만 만든다."""


def validate(doc_type: str, field_data: dict) -> list[str]:
    warnings = []
    if doc_type == "회의록":
        warnings += _validate_meeting(field_data)
    elif doc_type == "성과관리보고서":
        warnings += _validate_performance(field_data)
    elif doc_type == "교육결과보고서":
        warnings += _validate_education(field_data)
    elif doc_type == "협력활동보고서":
        warnings += _validate_cooperation(field_data)
    elif doc_type == "위촉장":
        warnings += _validate_appointment(field_data)
    return warnings


def _validate_meeting(d: dict) -> list[str]:
    w = []
    total = d.get("참석위원_총원") or 0
    external = d.get("참석위원_외부") or 0
    if total < 2:
        w.append("참석 위원이 2인 미만입니다 (2026년 필수 요건: 총 2인 이상).")
    if external < 1:
        w.append("외부 위원이 1인 이상 포함되어야 합니다.")
    opinions = d.get("위원의견") or []
    if total and len(opinions) < total:
        w.append(f"참석 위원 총원({total}명)에 비해 평가의견 입력 행이 부족합니다({len(opinions)}행).")
    return w


def _validate_performance(d: dict) -> list[str]:
    w = []
    members = d.get("평가위원명단") or []
    if len(members) < 2:
        w.append("평가위원이 2인 미만입니다 (2026년 필수 요건: 총 2인 이상).")
    if members and not any((m.get("구분") == "사외") for m in members):
        w.append("사외위원이 1인 이상 포함되어야 합니다.")
    criteria = d.get("측정기준") or []
    reports = d.get("성과보고") or []
    if len(criteria) != len(reports):
        w.append("① 측정기준과 ② 성과보고의 행 수가 다릅니다. 목표·지표가 일치해야 합니다.")
    else:
        for i, (c, r) in enumerate(zip(criteria, reports), start=1):
            if c.get("목표") and r.get("목표") and c.get("목표") != r.get("목표"):
                w.append(f"{i}번째 행: ①과 ②의 목표 문구가 다릅니다.")
    return w


def _validate_education(d: dict) -> list[str]:
    w = []
    attendee_count = d.get("참석인원") or 0
    roster = d.get("참석자명단") or []
    filled_roster = [r for r in roster if (r.get("성명") or "").strip()]
    if attendee_count and len(filled_roster) != attendee_count:
        w.append(f"참석인원({attendee_count}명)과 참석자 명단 입력 행 수({len(filled_roster)}행)가 일치하지 않습니다.")
    if not d.get("총교육시간"):
        w.append("총 교육시간이 입력되지 않았습니다.")
    if not filled_roster:
        w.append("참석자 명단이 비어 있습니다.")
    return w


def _validate_cooperation(d: dict) -> list[str]:
    w = []
    if not (d.get("상세1_협력기관명") or "").strip():
        w.append("협력활동 상세1의 협력기관명이 비어 있습니다.")
    return w


def _validate_appointment(d: dict) -> list[str]:
    w = []
    members = d.get("위원목록") or []
    if not members:
        w.append("위촉할 위원이 없습니다. 위원 1인당 1장이 생성됩니다.")
    for i, m in enumerate(members, start=1):
        start, end = m.get("위촉시작일"), m.get("위촉종료일")
        if start and end and start > end:
            w.append(f"{i}번째 위원: 위촉 시작일이 종료일보다 늦습니다.")
    return w
