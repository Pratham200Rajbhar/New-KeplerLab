"""Pydantic v2 schemas for Mind Map generation."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MindMapNode(BaseModel):
    id: str
    label: str
    parent_id: Optional[str] = None
    description: str
    question_hint: str
    has_children: bool = False


class MindMapRequest(BaseModel):
    notebook_id: str
    material_ids: List[str]


class MindMapResponse(BaseModel):
    id: str = ""
    title: str
    notebook_id: str = ""
    material_ids: List[str] = Field(default_factory=list)
    nodes: List[MindMapNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
