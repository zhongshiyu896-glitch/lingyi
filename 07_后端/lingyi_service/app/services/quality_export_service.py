"""Quality export formatter service (TASK-030F)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import csv
from io import BytesIO
from io import StringIO
import re
from typing import Iterable
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from app.schemas.quality import QualityInspectionDetailData


@dataclass(frozen=True)
class QualityExportArtifact:
    """Binary artifact for quality export downloads."""

    content: bytes
    content_type: str
    filename: str


class QualityExportService:
    """Build csv/xlsx/pdf export files from quality detail snapshots."""

    def build(
        self,
        *,
        export_format: str,
        details: list[QualityInspectionDetailData],
        inspection_id: int | None,
    ) -> QualityExportArtifact:
        fmt = export_format.lower()
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        if fmt == "csv":
            return QualityExportArtifact(
                content=self._build_csv(details),
                content_type="text/csv; charset=utf-8",
                filename=f"quality_export_{now}.csv",
            )
        if fmt == "xlsx":
            return QualityExportArtifact(
                content=self._build_xlsx(details),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"quality_export_{now}.xlsx",
            )
        if fmt == "pdf":
            if inspection_id is not None:
                single = details[0] if details else None
                content = self._build_single_pdf(single) if single else self._build_single_pdf(None)
                suffix = f"{inspection_id}" if inspection_id else now
                return QualityExportArtifact(
                    content=content,
                    content_type="application/pdf",
                    filename=f"quality_report_{suffix}.pdf",
                )
            return QualityExportArtifact(
                content=self._build_pdf_zip(details),
                content_type="application/zip",
                filename=f"quality_reports_{now}.zip",
            )
        raise ValueError("Unsupported export format")

    def _build_csv(self, details: list[QualityInspectionDetailData]) -> bytes:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "inspection_no",
                "company",
                "item_code",
                "supplier",
                "warehouse",
                "inspection_date",
                "inspected_qty",
                "accepted_qty",
                "rejected_qty",
                "defect_qty",
                "result",
                "status",
            ]
        )
        for detail in details:
            writer.writerow(
                [
                    detail.inspection_no,
                    detail.company,
                    detail.item_code,
                    detail.supplier or "",
                    detail.warehouse or "",
                    detail.inspection_date.isoformat(),
                    self._num(detail.inspected_qty),
                    self._num(detail.accepted_qty),
                    self._num(detail.rejected_qty),
                    self._num(detail.defect_qty),
                    detail.result,
                    detail.status,
                ]
            )
        text = output.getvalue()
        return text.encode("utf-8-sig")

    def _build_xlsx(self, details: list[QualityInspectionDetailData]) -> bytes:
        inspection_rows: list[list[str]] = [
            [
                "检验单号",
                "公司",
                "来源类型",
                "来源单号",
                "物料",
                "供应商",
                "仓库",
                "检验日期",
                "检验数量",
                "合格数量",
                "不合格数量",
                "缺陷数量",
                "结果",
                "状态",
            ]
        ]
        item_rows: list[list[str]] = [["检验单号", "行号", "物料", "抽检数量", "合格数量", "不合格数量", "缺陷数量", "结果", "备注"]]
        defect_rows: list[list[str]] = [["检验单号", "缺陷编码", "缺陷名称", "缺陷数量", "严重级别", "备注"]]
        log_rows: list[list[str]] = [["检验单号", "动作", "操作人", "时间", "原状态", "目标状态", "备注"]]

        for detail in details:
            inspection_rows.append(
                [
                    detail.inspection_no,
                    detail.company,
                    detail.source_type,
                    detail.source_id or "",
                    detail.item_code,
                    detail.supplier or "",
                    detail.warehouse or "",
                    detail.inspection_date.isoformat(),
                    self._num(detail.inspected_qty),
                    self._num(detail.accepted_qty),
                    self._num(detail.rejected_qty),
                    self._num(detail.defect_qty),
                    detail.result,
                    detail.status,
                ]
            )
            for item in detail.items:
                item_rows.append(
                    [
                        detail.inspection_no,
                        str(item.line_no),
                        item.item_code,
                        self._num(item.sample_qty),
                        self._num(item.accepted_qty),
                        self._num(item.rejected_qty),
                        self._num(item.defect_qty),
                        item.result,
                        item.remark or "",
                    ]
                )
            for defect in detail.defects:
                defect_rows.append(
                    [
                        detail.inspection_no,
                        defect.defect_code,
                        defect.defect_name,
                        self._num(defect.defect_qty),
                        defect.severity,
                        defect.remark or "",
                    ]
                )
            for log in detail.logs:
                log_rows.append(
                    [
                        detail.inspection_no,
                        log.action,
                        log.operator,
                        log.operated_at.isoformat(),
                        log.from_status or "",
                        log.to_status,
                        log.remark or "",
                    ]
                )

        sheets = [
            ("检验单", inspection_rows),
            ("检验明细", item_rows),
            ("缺陷记录", defect_rows),
            ("操作日志", log_rows),
        ]
        return self._build_xlsx_bytes(sheets)

    def _build_single_pdf(self, detail: QualityInspectionDetailData | None) -> bytes:
        if detail is None:
            lines = ["Quality Inspection Report", "No data"]
        else:
            lines = [
                f"Inspection No: {detail.inspection_no}",
                f"Company: {detail.company}",
                f"Item Code: {detail.item_code}",
                f"Supplier: {detail.supplier or '-'}",
                f"Warehouse: {detail.warehouse or '-'}",
                f"Inspection Date: {detail.inspection_date.isoformat()}",
                f"Inspected Qty: {self._num(detail.inspected_qty)}",
                f"Accepted Qty: {self._num(detail.accepted_qty)}",
                f"Rejected Qty: {self._num(detail.rejected_qty)}",
                f"Defect Qty: {self._num(detail.defect_qty)}",
                f"Result: {detail.result}",
                f"Status: {detail.status}",
                "",
                "Items:",
            ]
            for item in detail.items:
                lines.append(
                    f"- line={item.line_no} item={item.item_code} sample={self._num(item.sample_qty)} accepted={self._num(item.accepted_qty)} rejected={self._num(item.rejected_qty)}"
                )
            lines.append("")
            lines.append("Defects:")
            for defect in detail.defects:
                lines.append(
                    f"- code={defect.defect_code} name={defect.defect_name} qty={self._num(defect.defect_qty)} severity={defect.severity}"
                )
            lines.append("")
            lines.append("Logs:")
            for log in detail.logs:
                lines.append(
                    f"- action={log.action} operator={log.operator} to={log.to_status} time={log.operated_at.isoformat()}"
                )
        return self._build_plain_text_pdf(lines)

    def _build_pdf_zip(self, details: list[QualityInspectionDetailData]) -> bytes:
        output = BytesIO()
        with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zf:
            for detail in details:
                name = f"quality_report_{self._safe_name(detail.inspection_no)}.pdf"
                zf.writestr(name, self._build_single_pdf(detail))
        return output.getvalue()

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:80]

    @staticmethod
    def _num(value: Decimal | str | int | float) -> str:
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)

    def _build_plain_text_pdf(self, lines: Iterable[str]) -> bytes:
        escaped_lines = [self._escape_pdf_text(line) for line in lines]
        y = 800
        content_lines = ["BT", "/F1 10 Tf", "50 820 Td"]
        first = True
        for line in escaped_lines:
            if not first:
                y -= 14
                content_lines.append("0 -14 Td")
            first = False
            content_lines.append(f"({line}) Tj")
            if y <= 40:
                break
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")

        objects: list[bytes] = []
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objects.append(b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n")
        objects.append(
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n"
        )
        objects.append(b"4 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n")
        objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        output = BytesIO()
        output.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(output.tell())
            output.write(obj)
        xref_pos = output.tell()
        output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.write(
            (
                "trailer\n"
                f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                "startxref\n"
                f"{xref_pos}\n"
                "%%EOF"
            ).encode("ascii")
        )
        return output.getvalue()

    @staticmethod
    def _escape_pdf_text(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _build_xlsx_bytes(self, sheets: list[tuple[str, list[list[str]]]]) -> bytes:
        output = BytesIO()
        with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", self._content_types_xml(len(sheets)))
            zf.writestr("_rels/.rels", self._root_rels_xml())
            zf.writestr("xl/workbook.xml", self._workbook_xml(sheets))
            zf.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml(len(sheets)))
            zf.writestr("xl/styles.xml", self._styles_xml())
            for index, (_, rows) in enumerate(sheets, start=1):
                zf.writestr(f"xl/worksheets/sheet{index}.xml", self._sheet_xml(rows))
        return output.getvalue()

    @staticmethod
    def _content_types_xml(sheet_count: int) -> str:
        overrides = [
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        ]
        overrides.extend(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides)
            + "</Types>"
        )

    @staticmethod
    def _root_rels_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

    def _workbook_xml(self, sheets: list[tuple[str, list[list[str]]]]) -> str:
        sheet_nodes = []
        for index, (name, _) in enumerate(sheets, start=1):
            escaped = self._xml_escape(name)
            sheet_nodes.append(
                f'<sheet name="{escaped}" sheetId="{index}" r:id="rId{index}"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            + "".join(sheet_nodes)
            + '</sheets></workbook>'
        )

    @staticmethod
    def _workbook_rels_xml(sheet_count: int) -> str:
        rels = []
        for index in range(1, sheet_count + 1):
            rels.append(
                f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            )
        rels.append(
            f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels)
            + '</Relationships>'
        )

    @staticmethod
    def _styles_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '</styleSheet>'
        )

    def _sheet_xml(self, rows: list[list[str]]) -> str:
        row_nodes: list[str] = []
        for row_index, row in enumerate(rows, start=1):
            cell_nodes: list[str] = []
            for col_index, value in enumerate(row, start=1):
                cell_ref = f"{self._column_name(col_index)}{row_index}"
                cell_nodes.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{self._xml_escape(str(value))}</t></is></c>'
                )
            row_nodes.append(f'<row r="{row_index}">{"".join(cell_nodes)}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData>'
            + "".join(row_nodes)
            + '</sheetData></worksheet>'
        )

    @staticmethod
    def _column_name(index: int) -> str:
        result = ""
        current = index
        while current > 0:
            current, rem = divmod(current - 1, 26)
            result = chr(65 + rem) + result
        return result

    @staticmethod
    def _xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
