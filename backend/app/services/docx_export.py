"""Minimal, dependency-free .docx (WordprocessingML) writer.

python-docx isn't installable here (no PyPI access through the corporate proxy — see
09-ui-design-system.md / repo memory for the same constraint on the frontend side), so this
module hand-builds the OOXML package with the stdlib `zipfile` + `html.parser` only. It supports
exactly what the Monthly Meetings rich-text editor's toolbar allows: paragraphs, bold, italic,
underline, and bullet/ordered lists — enough to faithfully reproduce a meeting's notes, not a
general-purpose HTML-to-docx converter.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from xml.sax.saxutils import escape

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


@dataclass
class _Run:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class _Paragraph:
    kind: str = "normal"  # normal | heading | bullet | ordered
    runs: list[_Run] = field(default_factory=list)


class _NotesHtmlParser(HTMLParser):
    """Converts the rich-text editor's HTML into a flat list of styled paragraphs."""

    def __init__(self) -> None:
        super().__init__()
        self.paragraphs: list[_Paragraph] = []
        self._current: _Paragraph | None = None
        self._bold = 0
        self._italic = 0
        self._underline = 0
        self._list_stack: list[str] = []

    def _ensure(self, kind: str = "normal") -> None:
        if self._current is None:
            self._current = _Paragraph(kind)

    def _flush(self) -> None:
        if self._current is not None and (
            self._current.runs or self._current.kind != "normal"
        ):
            self.paragraphs.append(self._current)
        self._current = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("p", "div"):
            self._flush()
            self._ensure("normal")
        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
        elif tag == "li":
            self._flush()
            kind = "bullet" if self._list_stack and self._list_stack[-1] == "ul" else "ordered"
            self._ensure(kind)
        elif tag in ("strong", "b"):
            self._bold += 1
        elif tag in ("em", "i"):
            self._italic += 1
        elif tag == "u":
            self._underline += 1
        elif tag in ("h1", "h2", "h3"):
            self._flush()
            self._ensure("heading")
        elif tag == "br":
            self._flush()
            self._ensure("normal")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("p", "div", "li", "h1", "h2", "h3"):
            self._flush()
        elif tag in ("ul", "ol") and self._list_stack:
            self._list_stack.pop()
        elif tag in ("strong", "b"):
            self._bold = max(0, self._bold - 1)
        elif tag in ("em", "i"):
            self._italic = max(0, self._italic - 1)
        elif tag == "u":
            self._underline = max(0, self._underline - 1)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._ensure("normal")
        assert self._current is not None
        self._current.runs.append(
            _Run(data, bold=self._bold > 0, italic=self._italic > 0, underline=self._underline > 0)
        )

    def close(self) -> None:
        super().close()
        self._flush()


def _parse_notes_html(notes_html: str) -> list[_Paragraph]:
    parser = _NotesHtmlParser()
    parser.feed(notes_html or "")
    parser.close()
    return parser.paragraphs


def html_to_plain_text(notes_html: str, *, max_length: int | None = None) -> str:
    """Flattened preview text for the meetings list table (no markup)."""
    parts: list[str] = []
    for p in _parse_notes_html(notes_html):
        text = "".join(r.text for r in p.runs).strip()
        if text:
            parts.append(text)
    joined = " ".join(parts)
    joined = " ".join(joined.split())
    if max_length and len(joined) > max_length:
        return joined[: max_length - 1].rstrip() + "…"
    return joined


def _run_xml(run: _Run, *, force_bold: bool = False) -> str:
    props = ""
    if run.bold or force_bold:
        props += "<w:b/>"
    if run.italic:
        props += "<w:i/>"
    if run.underline:
        props += '<w:u w:val="single"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(run.text)}</w:t></w:r>'


def _paragraph_xml(paragraph: _Paragraph) -> str:
    is_heading = paragraph.kind == "heading"
    runs_xml = "".join(_run_xml(r, force_bold=is_heading) for r in paragraph.runs)
    if paragraph.kind == "bullet":
        runs_xml = _run_xml(_Run("\u2022 ")) + runs_xml
    if not runs_xml:
        runs_xml = '<w:r><w:t xml:space="preserve"></w:t></w:r>'
    return f"<w:p>{runs_xml}</w:p>"


def _page_break_xml() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def build_meeting_minutes_docx(entries: list[tuple[date, str]]) -> bytes:
    """Builds a .docx with one section per (meeting_date, notes_html) entry."""
    body_parts: list[str] = []
    for i, (meeting_date, notes_html) in enumerate(entries):
        if i > 0:
            body_parts.append(_page_break_xml())
        heading = _Paragraph("heading", [_Run(f"Meeting Date: {meeting_date.strftime('%d-%b-%Y')}")])
        body_parts.append(_paragraph_xml(heading))
        body_parts.append("<w:p/>")

        ordered_counter = 0
        for paragraph in _parse_notes_html(notes_html):
            if paragraph.kind == "ordered":
                ordered_counter += 1
                paragraph.runs = [_Run(f"{ordered_counter}. ")] + paragraph.runs
            else:
                ordered_counter = 0
            body_parts.append(_paragraph_xml(paragraph))

    body = "".join(body_parts)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body>"
        "</w:document>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("word/document.xml", document_xml)
    return buf.getvalue()