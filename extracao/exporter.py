from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import DocumentRecord, PipelineResult, TableRecord


class Exporter:
    def to_dataframe(self, records: list[DocumentRecord]) -> pd.DataFrame:
        return pd.DataFrame([record.to_dict() for record in records])

    def tables_to_dataframe(self, tables: list[TableRecord]) -> pd.DataFrame:
        return pd.DataFrame([table.to_dict() for table in tables])

    def export(self, result: PipelineResult, output_path: Path) -> Path:
        records_dataframe = self.to_dataframe(result.records)
        tables_dataframe = self.tables_to_dataframe(result.tables)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() in {".xlsx", ".xls"}:
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                records_dataframe.to_excel(writer, sheet_name="pages", index=False)
                tables_dataframe.to_excel(writer, sheet_name="tables", index=False)
        else:
            records_dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
            if not tables_dataframe.empty:
                tables_output = output_path.with_name(f"{output_path.stem}_tables{output_path.suffix}")
                tables_dataframe.to_csv(tables_output, index=False, encoding="utf-8-sig")
        return output_path
