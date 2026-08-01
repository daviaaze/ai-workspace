#!/usr/bin/env python3
"""Generate ATS-optimized CV as DOCX using only stdlib (zipfile + xml)."""

import zipfile, os
from xml.etree.ElementTree import Element, SubElement, tostring

WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def el(tag, parent=None, attrib=None, text=None):
    e = Element(f"{{{WML}}}{tag}", attrib=attrib or {})
    if parent is not None: parent.append(e)
    if text is not None: e.text = text
    return e

def add_rich_text(para, text, font_size="21", bold=False, bullet=False, color=None):
    """Add text with **bold** inline support."""
    if bullet:
        r = el("r", para)
        rPr = el("rPr", r)
        el("sz", rPr, {f"{{{WML}}}val": font_size})
        el("rFonts", rPr, {f"{{{WML}}}ascii": "Calibri", f"{{{WML}}}hAnsi": "Calibri"})
        el("t", r, text="\u2022 ", attrib={"xml:space": "preserve"})
    
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        r = el("r", para)
        rPr = el("rPr", r)
        el("sz", rPr, {f"{{{WML}}}val": font_size})
        el("rFonts", rPr, {f"{{{WML}}}ascii": "Calibri", f"{{{WML}}}hAnsi": "Calibri"})
        if color:
            el("color", rPr, {f"{{{WML}}}val": color})
        if bold or i % 2 == 1:
            el("b", rPr)
        el("t", r, text=part, attrib={"xml:space": "preserve"})

def add_section(doc_body, title, lines):
    """Add a titled section."""
    # Title
    p = el("p", doc_body)
    pPr = el("pPr", p)
    el("spacing", pPr, {f"{{{WML}}}before": "240", f"{{{WML}}}after": "80"})
    add_rich_text(p, title, font_size="24", bold=True)
    
    # Content lines
    for line in lines:
        if not line.strip():
            continue
        p = el("p", doc_body)
        pPr = el("pPr", p)
        el("spacing", pPr, {f"{{{WML}}}before": "40", f"{{{WML}}}after": "40"})
        
        stripped = line.strip()
        clean = stripped.replace("**", "")
        
        if stripped.startswith("**") and stripped.endswith("**"):
            add_rich_text(p, stripped, font_size="22", bold=True)
        elif stripped == "---":
            pBdr = el("pBdr", pPr)
            el("bottom", pBdr, {f"{{{WML}}}val": "single", f"{{{WML}}}sz": "4", f"{{{WML}}}space": "4", f"{{{WML}}}color": "999999"})
        elif stripped.startswith("###"):
            text = stripped.lstrip("# ")
            el("spacing", pPr, {f"{{{WML}}}before": "160", f"{{{WML}}}after": "40"})
            add_rich_text(p, text, font_size="22", bold=True)
        elif stripped.startswith("*"):
            text = stripped.lstrip("* ")
            el("ind", pPr, {f"{{{WML}}}left": "480", f"{{{WML}}}hanging": "240"})
            add_rich_text(p, text, font_size="21", bullet=True)
        elif stripped.startswith("##"):
            text = stripped.lstrip("# ")
            el("spacing", pPr, {f"{{{WML}}}before": "240", f"{{{WML}}}after": "60"})
            pBdr = el("pBdr", pPr)
            el("bottom", pBdr, {f"{{{WML}}}val": "single", f"{{{WML}}}sz": "4", f"{{{WML}}}space": "4", f"{{{WML}}}color": "555555"})
            add_rich_text(p, text, font_size="26", bold=True)
        else:
            add_rich_text(p, clean, font_size="21")


def main():
    md_path = "/home/daviaaze/Documents/Personal/carrer/Davi_Azevedo_CV_ATS_Optimized.md"
    output_path = "/home/daviaaze/Documents/Personal/carrer/Davi_Azevedo_CV_ATS_Optimized.docx"
    
    with open(md_path) as f:
        lines = f.readlines()
    
    document = Element(f"{{{WML}}}document", {
        f"xmlns:w": WML,
        f"xmlns:r": REL,
    })
    body = el("body", document)
    
    # === HEADER (centered name) ===
    name_line = lines[0].lstrip("# ").strip()
    p = el("p", body)
    pPr = el("pPr", p)
    el("jc", pPr, {f"{{{WML}}}val": "center"})
    el("spacing", pPr, {f"{{{WML}}}after": "40"})
    add_rich_text(p, name_line, font_size="36", bold=True, color="1a1a1a")
    
    # === CONTACT LINE ===
    contact = ""
    for line in lines[1:]:
        if line.strip() and not line.startswith("#") and "|" in line and "@" in line:
            contact = line.strip().replace("**", "")
            break
    
    if contact:
        p = el("p", body)
        pPr = el("pPr", p)
        el("jc", pPr, {f"{{{WML}}}val": "center"})
        el("spacing", pPr, {f"{{{WML}}}after": "60"})
        add_rich_text(p, contact, font_size="20", color="555555")
    
    # === SECTIONS ===
    # Parse markdown into sections
    current_section = None
    current_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("##"):
            continue  # skip main title
        if stripped.startswith("|") or "@" in stripped:
            continue  # skip contact line
        
        if stripped.startswith("## "):
            if current_section:
                add_section(body, current_section, current_lines)
            current_section = stripped[3:]
            current_lines = []
        elif current_section:
            current_lines.append(line.rstrip())
    
    if current_section and current_lines:
        add_section(body, current_section, current_lines)
    
    # Page setup
    sectPr = el("sectPr", body)
    el("pgSz", sectPr, {f"{{{WML}}}w": "12240", f"{{{WML}}}h": "15840"})
    el("pgMar", sectPr, {
        f"{{{WML}}}top": "600",
        f"{{{WML}}}right": "720",
        f"{{{WML}}}bottom": "600",
        f"{{{WML}}}left": "720",
        f"{{{WML}}}header": "360",
        f"{{{WML}}}footer": "360",
    })
    
    doc_xml = tostring(document, encoding="unicode", xml_declaration=True)
    
    # Create DOCX
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        z.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        z.writestr("word/_rels/document.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>''')
        z.writestr("word/document.xml", doc_xml)
    
    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ Created: {output_path} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()
