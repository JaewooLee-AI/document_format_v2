"""HWPX (한글 OWPML) 읽기/쓰기 어댑터.

HWPX는 zip 컨테이너 안에 Contents/section0.xml(OWPML) 을 담고 있다. 이 모듈은
section0.xml 안의 <hp:tbl> 표들을 (table_index, row, col) 논리 좌표로 접근하고,
그 외 zip 엔트리는 그대로 보존한 채 section0.xml만 다시 써서 저장한다.

표 순서/좌표는 engine.schema 에 정의된 스키마와 1:1로 대응한다(hwpx_forms/*.hwpx 실물을
직접 열어 확인한 좌표).
"""
import copy
import io
import zipfile
import xml.etree.ElementTree as ET

HP_URI = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HP = "{%s}" % HP_URI

NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": HP_URI,
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}
for _prefix, _uri in NAMESPACES.items():
    ET.register_namespace(_prefix, _uri)

XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
SECTION0_PATH = "Contents/section0.xml"
CONTENT_HPF_PATH = "Contents/content.hpf"
OPF_URI = "http://www.idpf.org/2007/opf/"
OPF = "{%s}" % OPF_URI


class HwpxDocument:
    def __init__(self, entries, section0_root):
        # entries: list[(filename, compress_type, bytes)] in original zip order.
        # Contents/section0.xml is kept live as an ElementTree (self._root);
        # Contents/content.hpf is parsed lazily only if a binary (사진) gets added.
        self._entries = entries
        self._root = section0_root
        self._tables = list(self._root.iter(HP + "tbl"))
        self._hpf_root = None
        self._new_binaries = []  # list[(filename, bytes)]

    @classmethod
    def open(cls, data: bytes) -> "HwpxDocument":
        entries = []
        section0_bytes = None
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                content = zf.read(info.filename)
                if info.filename == SECTION0_PATH:
                    section0_bytes = content
                entries.append((info.filename, info.compress_type, content))
        if section0_bytes is None:
            raise ValueError("Contents/section0.xml 이 없습니다 (hwpx 파일이 아님)")
        root = ET.fromstring(section0_bytes)
        return cls(entries, root)

    # -- 표 접근 -----------------------------------------------------------
    def table_count(self) -> int:
        return len(self._tables)

    def _table(self, table_index):
        return self._tables[table_index]

    def _cell(self, table_index, row, col):
        tbl = self._table(table_index)
        for tc in tbl.iter(HP + "tc"):
            addr = tc.find(HP + "cellAddr")
            if addr is not None and int(addr.get("rowAddr")) == row and int(addr.get("colAddr")) == col:
                return tc
        raise KeyError(f"cell not found: table={table_index} row={row} col={col}")

    def get_cell_text(self, table_index, row, col) -> str:
        tc = self._cell(table_index, row, col)
        return self._get_tc_text(tc)

    def set_cell_text(self, table_index, row, col, text: str):
        tc = self._cell(table_index, row, col)
        self._set_tc_text(tc, text or "")

    @staticmethod
    def _get_tc_text(tc) -> str:
        sublist = tc.find(HP + "subList")
        if sublist is None:
            return ""
        lines = []
        for p in sublist.findall(HP + "p"):
            lines.append("".join(t.text or "" for run in p.findall(HP + "run") for t in run.findall(HP + "t")))
        return "\n".join(lines)

    @staticmethod
    def _set_tc_text(tc, text: str):
        sublist = tc.find(HP + "subList")
        if sublist is None:
            raise ValueError("표 셀에 subList 가 없습니다 (지원하지 않는 셀 구조)")
        ps = list(sublist.findall(HP + "p"))
        template_p = ps[0] if ps else None
        for p in ps:
            sublist.remove(p)
        lines = text.split("\n") if text else [""]
        for i, line in enumerate(lines):
            if template_p is not None:
                new_p = copy.deepcopy(template_p)
            else:
                new_p = ET.Element(HP + "p", {"id": "0", "paraPrIDRef": "0", "styleIDRef": "0",
                                               "pageBreak": "0", "columnBreak": "0", "merged": "0"})
                ET.SubElement(new_p, HP + "run", {"charPrIDRef": "0"})
            new_p.set("id", str(i))
            for seg in list(new_p.findall(HP + "linesegarray")):
                new_p.remove(seg)
            run = new_p.find(HP + "run")
            if run is None:
                run = ET.SubElement(new_p, HP + "run", {"charPrIDRef": "0"})
            for t in list(run.findall(HP + "t")):
                run.remove(t)
            t_el = ET.SubElement(run, HP + "t")
            t_el.text = line
            sublist.append(new_p)

    # -- 문단/런 접근 (위촉장 전용) -----------------------------------------
    def get_paragraph_run_text(self, table_index, row, col, paragraph_index, run_index) -> str:
        run = self._get_run(table_index, row, col, paragraph_index, run_index)
        t = run.find(HP + "t")
        return t.text or "" if t is not None else ""

    def set_paragraph_run_text(self, table_index, row, col, paragraph_index, run_index, text: str):
        run = self._get_run(table_index, row, col, paragraph_index, run_index)
        t = run.find(HP + "t")
        if t is None:
            t = ET.SubElement(run, HP + "t")
        t.text = text

    def _get_run(self, table_index, row, col, paragraph_index, run_index):
        tc = self._cell(table_index, row, col)
        sublist = tc.find(HP + "subList")
        ps = sublist.findall(HP + "p")
        p = ps[paragraph_index]
        runs = p.findall(HP + "run")
        return runs[run_index]

    # -- 반복행(표) 크기 조정 -----------------------------------------------
    def ensure_row_count(self, table_index, header_row: int, desired_data_rows: int):
        tbl = self._table(table_index)
        trs = list(tbl.findall(HP + "tr"))
        data_trs = trs[header_row + 1:]
        current = len(data_trs)
        if desired_data_rows > current:
            template_tr = data_trs[-1] if data_trs else trs[header_row]
            for i in range(current, desired_data_rows):
                new_tr = copy.deepcopy(template_tr)
                for tc in new_tr.findall(HP + "tc"):
                    addr = tc.find(HP + "cellAddr")
                    if addr is not None:
                        addr.set("rowAddr", str(header_row + 1 + i))
                tbl.append(new_tr)
        elif desired_data_rows < current:
            for tr in data_trs[desired_data_rows:]:
                tbl.remove(tr)
        tbl.set("rowCnt", str(header_row + 1 + desired_data_rows))

    def get_row_count(self, table_index, header_row: int) -> int:
        tbl = self._table(table_index)
        trs = list(tbl.findall(HP + "tr"))
        return max(0, len(trs) - header_row - 1)

    # -- 라벨/값 행이 번갈아 나오는 표(회의록 위원의견 등) 쌍 개수 조정 -------
    def set_pair_count(self, table_index, desired_pairs: int):
        tbl = self._table(table_index)
        trs = list(tbl.findall(HP + "tr"))
        current_pairs = len(trs) // 2
        if desired_pairs > current_pairs:
            label_tpl, value_tpl = trs[0], trs[1]
            for i in range(current_pairs, desired_pairs):
                new_label = copy.deepcopy(label_tpl)
                new_value = copy.deepcopy(value_tpl)
                for tc in new_label.findall(HP + "tc"):
                    addr = tc.find(HP + "cellAddr")
                    if addr is not None:
                        addr.set("rowAddr", str(2 * i))
                for tc in new_value.findall(HP + "tc"):
                    addr = tc.find(HP + "cellAddr")
                    if addr is not None:
                        addr.set("rowAddr", str(2 * i + 1))
                tbl.append(new_label)
                tbl.append(new_value)
        elif desired_pairs < current_pairs:
            for tr in trs[desired_pairs * 2:]:
                tbl.remove(tr)
        tbl.set("rowCnt", str(desired_pairs * 2))

    def get_pair_count(self, table_index) -> int:
        tbl = self._table(table_index)
        return len(list(tbl.findall(HP + "tr"))) // 2

    # -- 사진(BinData) 추가 --------------------------------------------------
    def add_binary(self, filename: str, content: bytes, item_id: str, media_type: str = "image/jpeg"):
        """BinData/*.jpg 를 zip에 추가하고 content.hpf manifest에 등록한다."""
        if self._hpf_root is None:
            hpf_bytes = dict((n, c) for n, _, c in self._entries)[CONTENT_HPF_PATH]
            self._hpf_root = ET.fromstring(hpf_bytes)
        manifest = self._hpf_root.find(OPF + "manifest")
        item = ET.SubElement(manifest, OPF + "item")
        item.set("id", item_id)
        item.set("href", filename)
        item.set("media-type", media_type)
        self._new_binaries.append((filename, content))

    # -- 저장 ---------------------------------------------------------------
    def to_bytes(self) -> bytes:
        section0_body = ET.tostring(self._root, encoding="unicode")
        section0_bytes = XML_DECLARATION + section0_body.encode("utf-8")
        hpf_bytes = None
        if self._hpf_root is not None:
            hpf_bytes = XML_DECLARATION + ET.tostring(self._hpf_root, encoding="unicode").encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for filename, compress_type, content in self._entries:
                if filename == SECTION0_PATH:
                    zf.writestr(filename, section0_bytes, compress_type=compress_type)
                elif filename == CONTENT_HPF_PATH and hpf_bytes is not None:
                    zf.writestr(filename, hpf_bytes, compress_type=compress_type)
                else:
                    zf.writestr(filename, content, compress_type=compress_type)
            for filename, content in self._new_binaries:
                zf.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)
        return buf.getvalue()
