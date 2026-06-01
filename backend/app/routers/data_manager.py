"""Data manager router – export, import, CSV import, HTML import."""

from __future__ import annotations

import csv
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.database import DATABASE_PATH
from app.models import Portfolio, Watchlist, TradeLog
from app.security import export_database, import_database

router = APIRouter()


# ==================================================================== #
# Request schemas
# ==================================================================== #
class ExportRequest(BaseModel):
    password: str
    output_path: str


class ImportRequest(BaseModel):
    file_path: str
    password: str


class CsvImportRequest(BaseModel):
    file_path: str


class HtmlImportRequest(BaseModel):
    file_path: str


# ==================================================================== #
# POST /export
# ==================================================================== #
@router.post("/export")
async def export_data(request: ExportRequest) -> dict:
    """Export database to an encrypted .redpepper file."""
    try:
        export_database(str(DATABASE_PATH), request.password, request.output_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {exc}",
        ) from exc
    return {"message": "Export successful", "path": request.output_path}


# ==================================================================== #
# POST /import
# ==================================================================== #
@router.post("/import")
async def import_data(request: ImportRequest) -> dict:
    """Import a .redpepper file: decrypt, validate SQLite, replace current DB."""
    db_path = str(DATABASE_PATH)

    # Decrypt to a temporary file
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        import_database(request.file_path, request.password, tmp_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decryption failed: {exc}",
        ) from exc

    # Validate that it is a valid SQLite database
    try:
        conn = sqlite3.connect(tmp_path)
        conn.execute("PRAGMA schema_version")
        conn.close()
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SQLite database: {exc}",
        ) from exc

    # Replace current database (backup first)
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        shutil.copy2(tmp_path, db_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replace database: {exc}",
        ) from exc
    finally:
        os.unlink(tmp_path)

    return {"message": "Import successful", "backup": backup_path}


# ==================================================================== #
# POST /import-csv
# ==================================================================== #
@router.post("/import-csv")
async def import_csv(
    request: CsvImportRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Import portfolio data from a CSV file."""
    created = 0
    errors: list[str] = []

    try:
        with open(request.file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_num, row in enumerate(reader, start=2):
                try:
                    item = _row_to_portfolio(row)
                    db.add(item)
                    created += 1
                except Exception as exc:
                    errors.append(f"Row {row_num}: {exc}")
        db.commit()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV read error: {exc}",
        ) from exc

    return {"created": created, "errors": errors}


def _row_to_portfolio(row: dict[str, str]) -> Portfolio:
    """Map a CSV row to a Portfolio model instance."""

    def _f(val: str | None) -> float | None:
        if val is None:
            return None
        val = val.strip()
        return float(val) if val != "" else None

    def _i(val: str | None) -> int | None:
        if val is None:
            return None
        val = val.strip()
        return int(val) if val != "" else None

    return Portfolio(
        code=row.get("code", "").strip(),
        name=row.get("name", "").strip() or "",
        type=row.get("type", "").strip() or "ETF",
        account=row.get("account", "").strip() or "中信",
        sector=row.get("sector", "").strip() or None,
        amount=_f(row.get("amount")),
        profit=_f(row.get("profit")),
        cost_price=_f(row.get("cost_price")),
        current_price=_f(row.get("current_price")),
        shares=_i(row.get("shares")),
        reason=row.get("reason", "").strip() or None,
        target=row.get("target", "").strip() or None,
    )


# ==================================================================== #
# POST /import-html
# ==================================================================== #
@router.post("/import-html")
async def import_html(
    request: HtmlImportRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Parse AGI2Rich HTML/MD format and extract portfolio / watchlist / log data."""
    from html.parser import HTMLParser

    results: dict[str, Any] = {"portfolio": 0, "watchlist": 0, "trade_log": 0}

    try:
        with open(request.file_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot read file: {exc}",
        ) from exc

    # Simple HTML parser to extract tables
    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.tables: list[list[dict[str, str]]] = []
            self._current_table: list[dict[str, str]] = []
            self._current_row: dict[str, str] = {}
            self._headers: list[str] = []
            self._in_table = False
            self._in_row = False
            self._in_header = False
            self._in_cell = False
            self._cell_data = ""

        def handle_starttag(self, tag: str, attrs: Any) -> None:
            if tag == "table":
                self._in_table = True
                self._current_table = []
            elif tag == "tr":
                self._in_row = True
                self._current_row = {}
            elif tag in ("th", "td"):
                self._in_cell = True
                self._cell_data = ""
                if tag == "th":
                    self._in_header = True

        def handle_endtag(self, tag: str) -> None:
            if tag in ("th", "td"):
                cell = self._cell_data.strip()
                if self._in_header:
                    self._headers.append(cell)
                elif self._in_row:
                    idx = len(self._current_row)
                    if idx < len(self._headers):
                        self._current_row[self._headers[idx]] = cell
                self._in_cell = False
                self._in_header = False
            elif tag == "tr" and self._in_row:
                if self._current_row:
                    self._current_table.append(self._current_row)
                self._in_row = False
            elif tag == "table":
                if self._current_table:
                    self.tables.append(self._current_table)
                self._in_table = False
                self._headers = []

        def handle_data(self, data: str) -> None:
            if self._in_cell:
                self._cell_data += data

    parser = _TableParser()
    parser.feed(content)

    # Process extracted tables – heuristically determine type by headers
    for table in parser.tables:
        if not table:
            continue
        headers = set(table[0].keys())

        # Portfolio: has code and cost/price columns
        if {"code", "cost_price"} <= headers or {"code", "amount"} <= headers:
            for row in table:
                try:
                    db.add(_row_to_portfolio(row))
                    results["portfolio"] += 1
                except Exception:
                    pass

        # Watchlist: has code but no cost_price
        elif "code" in headers and "cost_price" not in headers:
            for row in table:
                try:
                    db.add(
                        Watchlist(
                            code=row.get("code", "").strip(),
                            name=row.get("name", "").strip() or "",
                            type=row.get("type", "").strip() or "股票",
                            sector=row.get("sector", "").strip() or None,
                            reason=row.get("reason", "").strip() or None,
                            trigger_condition=row.get("trigger_condition", "").strip() or None,
                            rating=row.get("rating", "").strip() or "⭐⭐⭐",
                            status=row.get("status", "").strip() or "观察",
                        ),
                    )
                    results["watchlist"] += 1
                except Exception:
                    pass

        # Trade log: has action/date
        elif "action" in headers or "date" in headers:
            for row in table:
                try:
                    db.add(
                        TradeLog(
                            code=row.get("code", "").strip(),
                            name=row.get("name", "").strip() or "",
                            action=row.get("action", "").strip() or "",
                            date=row.get("date", "").strip() or "",
                            amount=_parse_float(row.get("amount")),
                            reason=row.get("reason", "").strip() or None,
                            emotion=row.get("emotion", "").strip() or None,
                        ),
                    )
                    results["trade_log"] += 1
                except Exception:
                    pass

    db.commit()
    return {"message": "HTML import finished", "results": results}


def _parse_float(val: str | None) -> float | None:
    if val is None:
        return None
    val = val.strip()
    return float(val) if val != "" else None
