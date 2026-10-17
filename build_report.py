from __future__ import annotations

import html
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "report_tools"))

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
DRAFT = ROOT / "REPORT_CONTENT_DRAFT.md"
ASSET_DIR = ROOT / "report_assets"
DIAGRAM_DIR = ASSET_DIR / "diagrams"
SCREENSHOT_DIR = ASSET_DIR / "screenshots"
OUT_DOCX = ROOT / "DYNAMIC_LEARNING_PROJECT_REPORT.docx"
OUT_PDF = ROOT / "DYNAMIC_LEARNING_PROJECT_REPORT.pdf"

ATTACHMENT_DIR = ROOT / ".opencode" / "omnirush" / "inbox" / "chat-attachments" / "ses_ed0450c0fffeZVg555C4wQSOSm"
CERTIFICATE_NAME = "dvein certificate.jpeg"
SCREENSHOT_TIMES = [
    "2026-10-13 082408",
    "2026-10-13 082345",
    "2026-10-13 082335",
    "2026-10-13 082255",
    "2026-10-13 081958",
    "2026-10-13 081913",
    "2026-10-13 081804",
    "2026-10-13 081711",
    "2026-10-12 180747",
    "2026-10-12 180728",
    "2026-10-12 180703",
    "2026-10-12 180653",
    "2026-10-12 180637",
    "2026-10-12 180624",
]

GREEN = RGBColor(22, 75, 52)
GOLD = RGBColor(166, 104, 32)
GRAY = RGBColor(90, 99, 94)


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if edge in kwargs:
            edge_data = kwargs.get(edge)
            tag = "w:{}".format(edge)
            element = borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                borders.append(element)
            for key in ["val", "sz", "space", "color"]:
                if key in edge_data:
                    element.set(qn("w:{}".format(key)), str(edge_data[key]))


def add_page_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def add_field(paragraph, instruction: str, placeholder: str = ""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " " + instruction + " "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    if placeholder:
        text = OxmlElement("w:t")
        text.text = placeholder
        run._r.append(text)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])
    return run


def add_page_numbering(section, fmt: str, start: int = 1):
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    if pg_num is None:
        pg_num = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num)
    pg_num.set(qn("w:fmt"), fmt)
    pg_num.set(qn("w:start"), str(start))
    section.footer.is_linked_to_previous = False
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_p.text = ""
    add_page_field(footer_p)
    for run in footer_p.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)


def configure_section(section):
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(22)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(25)
    section.right_margin = Mm(20)


def style_document(doc: Document):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color in [("Heading 1", 16, GREEN), ("Heading 2", 13, GREEN), ("Heading 3", 11.5, GREEN), ("Heading 4", 11, GRAY)]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(10 if name != "Heading 4" else 6)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True

    caption = styles["Caption"]
    caption.font.name = "Times New Roman"
    caption.font.size = Pt(10)
    caption.font.italic = True
    caption.font.color.rgb = GRAY
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(8)


def add_rich_text(paragraph, text: str, justify: bool = True):
    if justify:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)")
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            paragraph.add_run(text[pos:match.start()])
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
        pos = match.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def add_paragraph(doc, text: str, style=None, align=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    add_rich_text(p, text, justify=align is None)
    return p


def add_bullets(doc, lines, numbered=False):
    style = "List Bullet" if not numbered else None
    for index, line in enumerate(lines, start=1):
        content = re.sub(r"^(?:\d+\.|[-*])\s+", "", line).strip()
        p = doc.add_paragraph(style=style)
        if numbered:
            p.paragraph_format.left_indent = Mm(8)
            p.paragraph_format.first_line_indent = Mm(-6)
            p.add_run(f"{index}. ")
        add_rich_text(p, content, justify=False)
        p.paragraph_format.space_after = Pt(2)


def split_table(lines):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            rows.append(cells)
    return rows


def add_markdown_table(doc, rows, caption=None):
    if not rows:
        return
    if caption:
        cap = doc.add_paragraph(style="Caption")
        cap.add_run(caption)
    cols = max(len(row) for row in rows)
    table = doc.add_table(rows=1, cols=cols)
    table.style = "Table Grid"
    table.autofit = True
    header = table.rows[0].cells
    for i in range(cols):
        text = rows[0][i] if i < len(rows[0]) else ""
        header[i].text = ""
        p = header[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_shading(header[i], "1E5A43")
        header[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for row in rows[1:]:
        cells = table.add_row().cells
        for i in range(cols):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            value = row[i] if i < len(row) else ""
            add_rich_text(p, value, justify=False)
            for run in p.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(8.5)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_code_block(doc, lines):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Mm(8)
    p.paragraph_format.right_indent = Mm(8)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.0
    for index, line in enumerate(lines):
        run = p.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(9)
        if index != len(lines) - 1:
            run.add_break()
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F1F5F2")
    p_pr.append(shd)


def copy_assets():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for index, stamp in enumerate(SCREENSHOT_TIMES, start=1):
        matches = list(ATTACHMENT_DIR.glob(f"Screenshot {stamp}.png"))
        if not matches:
            matches = list(ATTACHMENT_DIR.glob(f"*Screenshot {stamp}.png"))
        if matches:
            target = SCREENSHOT_DIR / f"screenshot_{index:02d}_{stamp.replace(' ', '_').replace('-', '')}.png"
            shutil.copy2(matches[0], target)
            copied.append(target)
    certificate = ATTACHMENT_DIR / CERTIFICATE_NAME
    if not certificate.exists():
        matches = list(ATTACHMENT_DIR.glob(f"*{CERTIFICATE_NAME}"))
        certificate = matches[0] if matches else certificate
    if certificate.exists():
        target = SCREENSHOT_DIR / "internship_certificate.jpeg"
        shutil.copy2(certificate, target)
    return copied


def extract_sections(text: str):
    abstract = text.split("## Abstract", 1)[1].split("# Chapter 1", 1)[0].strip()
    body = "# Chapter 1" + text.split("# Chapter 1", 1)[1].split("# Appendices", 1)[0]
    body = body.strip()
    references = text.split("# References", 1)[1].strip()
    return abstract, body, references


def add_figure(doc, figure_no: str, title: str, image_path: Path):
    if not image_path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(6.35))
    caption = doc.add_paragraph(style="Caption")
    caption.add_run(f"Figure {figure_no}: {title}")


def add_body_from_markdown(doc, body: str, diagram_map: dict[str, Path]):
    lines = body.splitlines()
    i = 0
    in_code = False
    code_lines = []
    table_captions = [
        "Table 3.1: Functional requirements",
        "Table 3.2: Non-functional requirements",
        "Table 5.1: Modules and responsibilities",
        "Table 6.1: Representative test plan and evidence",
        "Table 7.1: Synthetic offline benchmark results",
        "Table 7.2: Per-scenario synthetic results",
        "Table 7.3: Learning-rate sensitivity formula results",
        "Table 7.4: Learning-rate sensitivity replay",
    ]
    table_index = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("```"):
            if in_code:
                add_code_block(doc, code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if line.startswith("**[Figure"):
            match = re.search(r"Figure\s+(\d+\.\d+) insertion marker — (.*?): insert `([^`]+)`", line)
            if match:
                fig_no, title, filename = match.groups()
                add_figure(doc, fig_no, title, ROOT / filename)
            i += 1
            continue
        if line.startswith("**[Table"):
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1
            caption = table_captions[table_index] if table_index < len(table_captions) else None
            add_markdown_table(doc, split_table(table_lines), caption=caption)
            table_index += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1:
                if not title.startswith("Chapter 1") and doc.paragraphs and any(p.text.strip() for p in doc.paragraphs):
                    doc.add_page_break()
                add_paragraph(doc, title, style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
            else:
                add_paragraph(doc, title, style=f"Heading {level}", align=WD_ALIGN_PARAGRAPH.LEFT)
            i += 1
            continue
        if re.match(r"^(?:[-*])\s+", line):
            bullet_lines = []
            while i < len(lines) and re.match(r"^(?:[-*])\s+", lines[i].strip()):
                bullet_lines.append(lines[i].strip())
                i += 1
            add_bullets(doc, bullet_lines)
            continue
        if re.match(r"^\d+\.\s+", line):
            numbered_lines = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                numbered_lines.append(lines[i].strip())
                i += 1
            add_bullets(doc, numbered_lines, numbered=True)
            continue
        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4})\s+|^\||^\*\*\[|^```|^(?:[-*])\s+|^\d+\.\s+", lines[i]):
            paragraph_lines.append(lines[i].strip())
            i += 1
        add_paragraph(doc, " ".join(paragraph_lines))


def add_cover(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(35)
    r = p.add_run("DYNAMIC LEARNING")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(24)
    r.font.color.rgb = GREEN
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("PERSONALIZED LEARNING-RESOURCE RECOMMENDATION SYSTEM\nUSING LEARNER PROGRESS AND ADAPTIVE REVISION")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(15)
    p.paragraph_format.space_before = Pt(20)
    for text, size, italic in [
        ("A PROJECT REPORT", 15, False),
        ("Submitted by", 13, True),
        ("NOVIN KUMAR M (310123104068)", 15, False),
        ("In partial fulfillment for the award of the degree of", 12, True),
        ("BACHELOR OF ENGINEERING", 14, False),
        ("in", 12, True),
        ("COMPUTER SCIENCE AND ENGINEERING", 14, False),
        ("ANAND INSTITUTE OF HIGHER TECHNOLOGY", 14, False),
        ("(An Autonomous Institution)", 12, False),
        ("ANNA UNIVERSITY: CHENNAI 600 025", 13, False),
        ("OCTOBER 2026", 13, False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(10 if text not in {"Submitted by", "in"} else 15)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
        r.bold = not italic and text not in {"A PROJECT REPORT"}
        r.italic = italic
        if "ANAND" in text or "ANNA UNIVERSITY" in text:
            r.font.color.rgb = GREEN


def add_certificate_page(doc):
    for text, size in [
        ("ANAND INSTITUTE OF HIGHER TECHNOLOGY", 15),
        ("(An Autonomous Institution)", 11),
        ("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING", 13),
        ("BONAFIDE CERTIFICATE", 15),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
        r.bold = True
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Mm(10)
    p.paragraph_format.right_indent = Mm(10)
    add_rich_text(p, 'Certified that this project "DYNAMIC LEARNING — PERSONALIZED LEARNING-RESOURCE RECOMMENDATION SYSTEM USING LEARNER PROGRESS AND ADAPTIVE REVISION" is the bonafide work of NOVIN KUMAR M (310123104068) who carried out the project work under the guidance and supervision of the department.')
    doc.add_paragraph("\n\n")
    table = doc.add_table(rows=1, cols=2)
    table.autofit = True
    table.style = "Table Grid"
    for cell, role in zip(table.rows[0].cells, ["HEAD OF THE DEPARTMENT", "SUPERVISOR"]):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("SIGNATURE\n\nMrs. M. Maheshwari, M.E., (Ph.D.)\n" + role + "\nDepartment of Computer Science and Engineering\nAnand Institute of Higher Technology")
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.bold = True
        set_cell_border(cell, top={"val": "nil"}, bottom={"val": "nil"}, left={"val": "nil"}, right={"val": "nil"})
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(45)
    p.add_run("Submitted for University Examination held in October 2026").font.size = Pt(11)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(45)
    p.add_run("INTERNAL EXAMINER                                      EXTERNAL EXAMINER").bold = True


def add_acknowledgement(doc):
    add_paragraph(doc, "ACKNOWLEDGEMENT", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    paragraphs = [
        "I express my sincere gratitude to the management and faculty of Anand Institute of Higher Technology for providing the facilities and encouragement required to complete this project.",
        "I extend my heartfelt thanks to Mrs. M. Maheshwari, M.E., (Ph.D.), Head of the Department of Computer Science and Engineering, for her support and guidance throughout the project work.",
        "I also thank the teaching and non-teaching staff members of the Department of Computer Science and Engineering for their valuable assistance, suggestions, and encouragement.",
        "Finally, I thank my family and friends for their continuous support and motivation during the development, testing, and documentation of Dynamic Learning.",
    ]
    for text in paragraphs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Mm(10)
        add_rich_text(p, text)


def add_front_matter(doc, abstract: str):
    add_paragraph(doc, "ABSTRACT", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    for block in abstract.split("\n\n"):
        add_paragraph(doc, block.strip())
    doc.add_page_break()
    add_paragraph(doc, "TABLE OF CONTENTS", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    toc = doc.add_paragraph()
    toc.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_field(toc, 'TOC \\o "1-3" \\h \\z \\u')
    doc.add_page_break()
    add_paragraph(doc, "LIST OF FIGURES", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    figures = [
        ("4.1", "Proposed system architecture"),
        ("4.2", "Learner workflow and recommendation loop"),
        ("4.3", "Use-case diagram"),
        ("4.4", "Core data model"),
        ("4.5", "Quiz submission and adaptation activity"),
        ("4.6", "Recommendation-generation sequence"),
    ]
    for no, title in figures:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Mm(15)
        p.add_run(f"Figure {no}\t{title}")
    doc.add_page_break()
    add_paragraph(doc, "LIST OF TABLES", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    tables = [
        ("3.1", "Functional requirements"),
        ("3.2", "Non-functional requirements"),
        ("5.1", "Modules and responsibilities"),
        ("6.1", "Representative test plan and evidence"),
        ("7.1", "Synthetic offline benchmark results"),
        ("7.2", "Per-scenario synthetic results"),
        ("7.3", "Learning-rate sensitivity formula results"),
        ("7.4", "Learning-rate sensitivity replay"),
    ]
    for no, title in tables:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Mm(15)
        p.add_run(f"Table {no}\t{title}")


def add_appendices(doc, screenshots, certificate):
    doc.add_page_break()
    add_paragraph(doc, "APPENDIX 1 — SUPPLIED BASE PAPER", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "The supplied base paper for this project is Hongnan You, Lijun Xu, and Dongping Wu, “MFF-CF: A Multi-Feature Fused Collaborative Filtering Framework for Personalized Learning Resource Recommendation in Smart Education,” Discover Artificial Intelligence, volume 6, article 860, 2026, DOI: 10.1007/s44163-026-01715-0.")
    add_paragraph(doc, "Crossref metadata verified the publication identity, authors, journal, DOI, and online date of 21 August 2026. The full Springer article was not readable during the project audit because the publisher returned a client challenge. Dynamic Learning is not a reproduction of MFF-CF and does not implement collaborative filtering. This appendix therefore records the verified citation and project relationship rather than reproducing paper pages that were not supplied in readable form.")
    add_paragraph(doc, "The project instead investigates a narrower implementation question: how topic-level quiz evidence, explicit prerequisites, completion and revision rules, and recommendation reasons can be made visible and reproducible in a small local learner flow when collaborative interaction data is unavailable.")

    doc.add_page_break()
    add_paragraph(doc, "APPENDIX 2 — SCREENSHOTS", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "The following screenshots were supplied from the Dynamic Learning application and are included as visual evidence of the interface. They are not substituted with screenshots from the unrelated senior report. The captures represent different local states; some show completed badges while another dashboard capture reports zero overall completion. This apparent state difference is retained as supplied and is not used as a new functional-test claim.")
    captions = [
        "Recommendation evaluation benchmark",
        "Dashboard quiz history",
        "Dashboard topic-wise mastery",
        "Learning resource library",
        "Dashboard recommendations and weak topic",
        "Quiz feedback and adaptation summary",
        "Dashboard overview and recommendation queue",
        "Sign-in page",
        "Evaluation metrics with context",
        "Evaluation comparison with no comparison data",
        "Topic-wise mastery and quiz history",
        "Foundation quiz selection",
        "Recommendation explanations and library state",
        "Dashboard metrics and recommendation queue",
    ]
    for index in range(0, len(screenshots), 2):
        pair = screenshots[index:index + 2]
        for offset, image_path in enumerate(pair):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.add_run().add_picture(str(image_path), width=Inches(6.25))
            cap = doc.add_paragraph(style="Caption")
            cap.add_run(f"Screenshot {index + offset + 1}: {captions[index + offset] if index + offset < len(captions) else image_path.stem}")
        if index + 2 < len(screenshots):
            doc.add_page_break()

    doc.add_page_break()
    add_paragraph(doc, "APPENDIX 3 — INTERNSHIP CERTIFICATE", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "The supplied DVein Innovations internship completion certificate is reproduced below unchanged. It records a Full Stack with Java internship from 02/06/2026 to 02/07/2026. It is included as supporting academic material and is not evidence of Dynamic Learning ranking or learning outcomes.")
    if certificate and certificate.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(certificate), width=Inches(6.5))
    doc.add_page_break()
    add_paragraph(doc, "APPENDIX 4 — EVIDENCE AND DISCLOSURE NOTE", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_paragraph(doc, "The report distinguishes application evidence from research claims. Application evidence includes deterministic local behaviour, stored learner records, automated tests, HTTP persistence checks, and synthetic ranking calculations. The audit does not certify a superior recommender, unbiased effectiveness, novel research, real learning improvement, accurate forgetting detection, full-paper limitation claims, real-browser execution, production load/concurrency, or preservation and recovery of learner data that may have existed before the early workspace reset probe.")


def add_references(doc, references: str):
    doc.add_page_break()
    add_paragraph(doc, "REFERENCES", style="Heading 1", align=WD_ALIGN_PARAGRAPH.CENTER)
    for line in references.splitlines():
        if not line.strip():
            continue
        add_paragraph(doc, line.strip())


def update_and_export(docx_path: Path, pdf_path: Path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    document = None
    try:
        document = word.Documents.Open(str(docx_path.resolve()))
        document.Repaginate()
        document.Fields.Update()
        for toc in document.TablesOfContents:
            toc.Update()
        document.Fields.Update()
        document.Save()
        document.ExportAsFixedFormat(str(pdf_path.resolve()), 17)
    finally:
        if document is not None:
            document.Close(False)
        word.Quit()
        pythoncom.CoUninitialize()


def main():
    text = DRAFT.read_text(encoding="utf-8")
    abstract, body, references = extract_sections(text)
    screenshots = copy_assets()
    certificate = SCREENSHOT_DIR / "internship_certificate.jpeg"

    doc = Document()
    style_document(doc)
    for section in doc.sections:
        configure_section(section)
    cover_section = doc.sections[0]
    cover_section.different_first_page_header_footer = True
    add_cover(doc)

    front_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(front_section)
    add_page_numbering(front_section, "lowerRoman", 1)
    add_certificate_page(doc)
    doc.add_page_break()
    add_acknowledgement(doc)
    doc.add_page_break()
    add_front_matter(doc, abstract)

    main_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(main_section)
    add_page_numbering(main_section, "decimal", 1)
    main_section.header.is_linked_to_previous = False
    header = main_section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header.add_run("DYNAMIC LEARNING")
    header_run.font.name = "Times New Roman"
    header_run.font.size = Pt(9)
    header_run.font.color.rgb = GRAY

    diagram_map = {path.name: path for path in DIAGRAM_DIR.glob("*.png")}
    add_body_from_markdown(doc, body, diagram_map)
    add_appendices(doc, screenshots, certificate)
    add_references(doc, references)

    doc.core_properties.title = "Dynamic Learning — Project Report"
    doc.core_properties.subject = "Personalized learning-resource recommendation system"
    doc.core_properties.author = "Novin kumar M"
    doc.core_properties.keywords = "Dynamic Learning, recommender system, Flask, adaptive revision"
    doc.save(str(OUT_DOCX))
    update_and_export(OUT_DOCX, OUT_PDF)
    print(f"Created {OUT_DOCX.name} ({OUT_DOCX.stat().st_size} bytes)")
    print(f"Created {OUT_PDF.name} ({OUT_PDF.stat().st_size} bytes)")
    print(f"Copied {len(screenshots)} screenshots and certificate={certificate.exists()}")


if __name__ == "__main__":
    main()
