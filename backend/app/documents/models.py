"""نماذج المستندات."""

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    preview: str
    created_at: str


class DocumentContent(BaseModel):
    id: int
    filename: str
    content: str
