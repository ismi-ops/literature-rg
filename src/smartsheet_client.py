"""Smartsheet REST API client for reading and writing the paper repository."""
import requests
from src.config import COLUMN_IDS, SHEET_ID

SMARTSHEET_BASE = "https://api.smartsheet.com/2.0"


class SmartsheetClient:
    def __init__(self, api_key: str, sheet_id: int = SHEET_ID):
        self.sheet_id = sheet_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def get_existing_papers(self) -> set[str]:
        """
        Return a set of lowercase DOIs and titles already in the sheet,
        used for duplicate detection before writing.
        """
        col_ids = ",".join(str(v) for v in [
            COLUMN_IDS["title"], COLUMN_IDS["doi"]
        ])
        url = f"{SMARTSHEET_BASE}/sheets/{self.sheet_id}"
        params = {"columnIds": col_ids, "include": "cells"}

        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        existing: set[str] = set()
        for row in data.get("rows", []):
            for cell in row.get("cells", []):
                val = str(cell.get("value") or "").strip().lower()
                if val:
                    existing.add(val)

        return existing

    def add_paper(self, paper: dict) -> bool:
        """Add a single paper as a new bottom row in the sheet."""
        def cell(col_key: str, value) -> dict:
            return {"columnId": COLUMN_IDS[col_key], "value": value}

        paper_type = paper.get("type", "research")
        if paper_type not in ("research", "review", "perspective"):
            paper_type = "research"

        cells = [
            cell("title",         _truncate(paper.get("title", ""), 4000)),
            cell("authors",       _truncate(paper.get("authors", ""), 2000)),
            cell("year",          paper.get("year", "")),
            cell("journal",       paper.get("journal", "")),
            cell("type",          paper_type),
            cell("summary",       _truncate(paper.get("summary", ""), 4000)),
            cell("tags",          paper.get("tags", "")),
            cell("doi",           paper.get("doi", "")),
            cell("link",          paper.get("url", "")),
            cell("status",        "On deck for Ru"),
            cell("shared_with_ru", False),
        ]

        payload = {"rows": [{"toBottom": True, "cells": cells}]}
        url = f"{SMARTSHEET_BASE}/sheets/{self.sheet_id}/rows"

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return True
            print(f"    Smartsheet error {resp.status_code}: {resp.text[:300]}")
            return False
        except Exception as e:
            print(f"    Smartsheet exception: {e}")
            return False


def _truncate(value: str, max_len: int) -> str:
    return value[:max_len] if value else ""
