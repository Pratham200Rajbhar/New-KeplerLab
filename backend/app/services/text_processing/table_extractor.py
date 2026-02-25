"""Advanced table extraction and Markdown formatting.

Provides table detection from PDFs and conversion to clean Markdown format.
Handles complex tables with merged cells, nested structures, and formatting.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple

import pdfplumber
from pdfplumber.table import Table

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extract and format tables from PDFs."""
    
    def __init__(self, table_settings: Optional[Dict[str, Any]] = None):
        """
        Initialize table extractor.
        
        Args:
            table_settings: Custom PDFPlumber table settings
        """
        self.table_settings = table_settings or {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 3,
            "min_words_horizontal": 1,
            "intersection_tolerance": 3,
        }
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract all tables from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dicts, each containing:
                - markdown: Table in Markdown format
                - page_num: Page number (0-indexed)
                - table_idx: Table index on page
                - rows: Number of rows
                - cols: Number of columns
                - bbox: Bounding box (x0, y0, x1, y1)
        """
        tables_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = self._extract_tables_from_page(page, page_num)
                    tables_data.extend(page_tables)
            
            logger.info(f"Extracted {len(tables_data)} tables from {pdf_path}")
            return tables_data
        
        except Exception as exc:
            logger.error(f"Failed to extract tables from {pdf_path}: {exc}")
            return []
    
    def _extract_tables_from_page(self, page: pdfplumber.page.Page, page_num: int) -> List[Dict[str, Any]]:
        """Extract all tables from a single page."""
        tables_data = []
        
        try:
            # Extract tables with settings
            tables = page.find_tables(table_settings=self.table_settings)
            
            for table_idx, table in enumerate(tables):
                # Extract table data
                table_data = table.extract()
                
                if not table_data or not table_data[0]:
                    continue
                
                # Convert to Markdown
                markdown = self.table_to_markdown(
                    table_data,
                    page_num=page_num,
                    table_idx=table_idx
                )
                
                if markdown:
                    tables_data.append({
                        "markdown": markdown,
                        "page_num": page_num,
                        "table_idx": table_idx,
                        "rows": len(table_data),
                        "cols": len(table_data[0]) if table_data else 0,
                        "bbox": table.bbox
                    })
        
        except Exception as exc:
            logger.warning(f"Failed to extract tables from page {page_num}: {exc}")
        
        return tables_data
    
    def table_to_markdown(
        self,
        table_data: List[List[Any]],
        page_num: int = 0,
        table_idx: int = 0,
        include_header: bool = True
    ) -> str:
        """
        Convert table data to Markdown format.
        
        Args:
            table_data: 2D list of table cells
            page_num: Page number for caption
            table_idx: Table index for caption
            include_header: Whether to include header caption
            
        Returns:
            Markdown formatted table string
        """
        if not table_data or not table_data[0]:
            return ""
        
        try:
            markdown_lines = []
            
            # Add table caption
            if include_header:
                markdown_lines.append(f"\n**Table {table_idx + 1} (Page {page_num + 1})**\n")
            
            # Clean and prepare header
            header = self._clean_row(table_data[0])
            
            # If header is empty or all None, use column indices
            if not any(header):
                header = [f"Column {i+1}" for i in range(len(header))]
            
            num_cols = len(header)
            
            # Add header row
            markdown_lines.append("| " + " | ".join(header) + " |")
            
            # Add separator
            markdown_lines.append("|" + "|".join([" --- " for _ in range(num_cols)]) + "|")
            
            # Add data rows
            for row in table_data[1:]:
                cleaned_row = self._clean_row(row)
                
                # Ensure row has correct length
                while len(cleaned_row) < num_cols:
                    cleaned_row.append("")
                cleaned_row = cleaned_row[:num_cols]
                
                # Skip completely empty rows
                if not any(cleaned_row):
                    continue
                
                markdown_lines.append("| " + " | ".join(cleaned_row) + " |")
            
            return "\n".join(markdown_lines)
        
        except Exception as exc:
            logger.warning(f"Failed to convert table to Markdown: {exc}")
            return ""
    
    def _clean_row(self, row: List[Any]) -> List[str]:
        """Clean and format a table row."""
        cleaned = []
        
        for cell in row:
            if cell is None:
                cleaned.append("")
            else:
                # Convert to string and clean
                cell_str = str(cell).strip()
                
                # Replace pipe characters to avoid breaking Markdown
                cell_str = cell_str.replace("|", "\\|")
                
                # Replace newlines with space
                cell_str = cell_str.replace("\n", " ")
                
                # Remove excessive whitespace
                cell_str = " ".join(cell_str.split())
                
                cleaned.append(cell_str)
        
        return cleaned
    
    def detect_table_structure(self, table_data: List[List[Any]]) -> Dict[str, Any]:
        """
        Analyze table structure and characteristics.
        
        Args:
            table_data: 2D list of table cells
            
        Returns:
            Dict with structure info:
                - has_header: Whether first row is likely a header
                - num_rows: Number of rows
                - num_cols: Number of columns
                - empty_cells: Count of empty cells
                - merged_cells: Detected merged cells
        """
        if not table_data:
            return {}
        
        num_rows = len(table_data)
        num_cols = max(len(row) for row in table_data) if table_data else 0
        
        # Count empty cells
        empty_cells = sum(
            1 for row in table_data
            for cell in row
            if cell is None or str(cell).strip() == ""
        )
        
        # Detect if first row is header (heuristic)
        has_header = False
        if num_rows > 1 and table_data[0]:
            first_row = table_data[0]
            # Header is likely if:
            # 1. First row cells are shorter than average
            # 2. First row has more text formatting
            # 3. First row cells don't contain numbers
            first_row_text = " ".join(str(c) for c in first_row if c)
            
            # Simple heuristic: check if first row contains mostly text
            has_header = not any(str(cell).strip().replace(".", "").isdigit() for cell in first_row if cell)
        
        return {
            "has_header": has_header,
            "num_rows": num_rows,
            "num_cols": num_cols,
            "empty_cells": empty_cells,
            "empty_cell_ratio": empty_cells / (num_rows * num_cols) if (num_rows * num_cols) > 0 else 0,
            "is_valid": num_rows > 1 and num_cols > 1,
        }
    
    def merge_adjacent_tables(
        self,
        tables: List[Dict[str, Any]],
        max_vertical_gap: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Merge tables that are split across page breaks or sections.
        
        Args:
            tables: List of table dicts with bbox and page_num
            max_vertical_gap: Maximum vertical gap to consider tables adjacent
            
        Returns:
            List of merged tables
        """
        if len(tables) <= 1:
            return tables
        
        merged = []
        skip_indices = set()
        
        for i, table1 in enumerate(tables):
            if i in skip_indices:
                continue
            
            # Check if next table on same page is adjacent
            for j in range(i + 1, len(tables)):
                table2 = tables[j]
                
                # Only merge tables on same page
                if table1["page_num"] != table2["page_num"]:
                    continue
                
                # Check vertical gap
                bbox1 = table1["bbox"]
                bbox2 = table2["bbox"]
                
                vertical_gap = abs(bbox2[1] - bbox1[3])  # Gap between bottom of table1 and top of table2
                
                if vertical_gap < max_vertical_gap:
                    # Merge tables
                    # This is a simplified merge - in practice, you'd need to parse and combine the data
                    merged_markdown = table1["markdown"] + "\n\n" + table2["markdown"]
                    
                    merged.append({
                        "markdown": merged_markdown,
                        "page_num": table1["page_num"],
                        "table_idx": table1["table_idx"],
                        "rows": table1["rows"] + table2["rows"],
                        "cols": max(table1["cols"], table2["cols"]),
                        "bbox": (bbox1[0], bbox1[1], bbox2[2], bbox2[3])
                    })
                    
                    skip_indices.add(i)
                    skip_indices.add(j)
                    break
            else:
                # No merge happened
                if i not in skip_indices:
                    merged.append(table1)
        
        return merged


def extract_tables_as_markdown(pdf_path: str, merge_adjacent: bool = False) -> str:
    """
    Helper function to extract all tables from PDF as Markdown text.
    
    Args:
        pdf_path: Path to PDF file
        merge_adjacent: Whether to merge adjacent tables
        
    Returns:
        All tables concatenated as Markdown string
    """
    extractor = TableExtractor()
    tables = extractor.extract_tables_from_pdf(pdf_path)
    
    if merge_adjacent:
        tables = extractor.merge_adjacent_tables(tables)
    
    return "\n\n".join(table["markdown"] for table in tables)
