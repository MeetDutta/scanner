"""
Offline Synthetic Document Fixture Generator for SpecGuard.

Generates local test fixtures for automated testing:
1. 1-page PDF
2. 20-page PDF
3. 50-page PDF
4. 100-page PDF
5. Two-column IEEE-style PDF
6. Single-column engineering specification PDF
7. PDF containing tables
8. PDF containing figures
9. PDF containing equations
10. PDF containing a Table of Contents (TOC)
11. PDF containing multi-page split tables
12. Multi-page DOCX fixture
13. Corrupted PDF fixture
14. PDF with duplicate figure labels
15. PDF with unresolved cross-references
100% offline, zero internet or external downloads.
"""

from pathlib import Path
import pymupdf
import docx

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def create_1_page_pdf(path: Path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((54, 70), "1. Scope", fontsize=14, fontname="helv", color=(0, 0, 0))
    page.insert_text((54, 100), "This specification covers the mechanical design of steel shafts.", fontsize=11, fontname="helv")
    page.insert_text((54, 140), "2. Requirements", fontsize=14, fontname="helv")
    page.insert_text((54, 170), "Shaft diameter shall be 50 mm with a tolerance of ±0.05 mm.", fontsize=11, fontname="helv")
    page.insert_text((54, 210), "3. Testing", fontsize=14, fontname="helv")
    page.insert_text((54, 240), "Perform tensile testing at 25°C under 100 kN load.", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def create_n_page_pdf(path: Path, n_pages: int):
    doc = pymupdf.open()
    for i in range(1, n_pages + 1):
        page = doc.new_page(width=612, height=792)
        page.insert_text((54, 50), f"Engineering Specification — Document Volume {i}", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page.draw_line((54, 55), (558, 55), color=(0.7, 0.7, 0.7))

        page.insert_text((54, 90), f"Section {i}. General Requirements for Stage {i}", fontsize=14, fontname="helv")
        y = 120
        for p_idx in range(6):
            page.insert_text((54, y), f"Paragraph {p_idx + 1} detailing mechanical criteria, operating margins, and material limits for Page {i}.", fontsize=10, fontname="helv")
            y += 24

        page.draw_line((54, 740), (558, 740), color=(0.7, 0.7, 0.7))
        page.insert_text((280, 755), f"Page {i} of {n_pages}", fontsize=9, fontname="helv")
    doc.save(str(path))
    doc.close()


def create_ieee_two_column_pdf(path: Path):
    doc = pymupdf.open()
    # Page 1: Spanning Title + Abstract, then 2-column body
    p1 = doc.new_page(width=612, height=792)
    # Title (spanning)
    p1.insert_text((120, 60), "Deep Document Intelligence for IEEE Paper Compliance", fontsize=16, fontname="helv", color=(0, 0, 0))
    p1.insert_text((190, 85), "John Doe, Senior Member, IEEE, and Jane Smith", fontsize=10, fontname="helv")

    # Abstract (spanning)
    abstract_txt = (
        "Abstract—This paper introduces a real-time, offline document analysis pipeline for verifying "
        "format compliance, citation resolution, and multi-page structural integrity. We demonstrate automated "
        "evaluation of academic manuscripts across two-column layouts."
    )
    p1.insert_text((54, 115), abstract_txt[:120], fontsize=9, fontname="helv")
    p1.insert_text((54, 128), abstract_txt[120:], fontsize=9, fontname="helv")
    p1.insert_text((54, 145), "Index Terms—Document Intelligence, IEEE Compliance, Computer Vision.", fontsize=9, fontname="helv")

    # Column 1 (x: 54 to 285)
    p1.insert_text((54, 175), "I. INTRODUCTION", fontsize=11, fontname="helv")
    y = 195
    for idx in range(8):
        p1.insert_text((54, y), f"Text in column 1 line {idx+1} citing work [1] and [2].", fontsize=9, fontname="helv")
        y += 14

    p1.insert_text((54, y + 10), "A. System Architecture", fontsize=10, fontname="helv")
    y += 30
    for idx in range(6):
        p1.insert_text((54, y), f"Detailed architectural paragraph discussing model in Fig. 1.", fontsize=9, fontname="helv")
        y += 14

    # Column 2 (x: 325 to 558)
    p1.insert_text((325, 175), "II. RELATED WORK", fontsize=11, fontname="helv")
    y = 195
    for idx in range(8):
        p1.insert_text((325, y), f"Text in column 2 line {idx+1} referencing Table I and Eq. (1).", fontsize=9, fontname="helv")
        y += 14

    # Vector figure on page 1
    p1.draw_rect(pymupdf.Rect(325, 330, 550, 430), color=(0.2, 0.4, 0.8), width=1.5)
    p1.insert_text((380, 380), "[Pipeline Diagram]", fontsize=10, fontname="helv")
    p1.insert_text((340, 445), "Fig. 1. Architecture of the multi-page compliance analyzer.", fontsize=9, fontname="helv")

    # Display Equation in col 2
    p1.insert_text((350, 480), "E = m c^2 + a b", fontsize=10, fontname="helv")
    p1.insert_text((530, 480), "(1)", fontsize=10, fontname="helv")

    # Page 2: Conclusion & References
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((54, 70), "III. RESULTS AND CONCLUSION", fontsize=11, fontname="helv")
    p2.insert_text((54, 90), "The proposed offline analysis successfully detected all formatting deviations.", fontsize=9, fontname="helv")

    p2.insert_text((54, 130), "REFERENCES", fontsize=11, fontname="helv")
    p2.insert_text((54, 150), "[1] J. Doe, \"Document Intelligence Systems,\" IEEE Trans. Knowl. Eng., 2024.", fontsize=8.5, fontname="helv")
    p2.insert_text((54, 170), "[2] J. Smith, \"Structural Layout Analysis,\" in Proc. IEEE Conf. CVPR, 2023.", fontsize=8.5, fontname="helv")

    doc.save(str(path))
    doc.close()


def create_pdf_with_toc_and_drift(path: Path):
    doc = pymupdf.open()
    # Page 1: Title
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((150, 150), "Turbine Design Specification", fontsize=18, fontname="helv")

    # Page 2: Table of Contents with intentional page drift
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((54, 70), "Table of Contents", fontsize=14, fontname="helv")
    p2.insert_text((54, 110), "1. Scope .................................................... 3", fontsize=10, fontname="helv")
    p2.insert_text((54, 130), "2. Requirements ............................................. 5", fontsize=10, fontname="helv")  # Drift! Actually on Page 4
    p2.insert_text((54, 150), "3. Testing .................................................. 6", fontsize=10, fontname="helv")

    # Page 3: Scope
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((54, 70), "1. Scope", fontsize=14, fontname="helv")
    p3.insert_text((54, 100), "Scope of high-pressure turbine testing.", fontsize=10, fontname="helv")

    # Page 4: Requirements (TOC said Page 5 -> page drift!)
    p4 = doc.new_page(width=612, height=792)
    p4.insert_text((54, 70), "2. Requirements", fontsize=14, fontname="helv")
    p4.insert_text((54, 100), "Turbine blade clearance must not exceed 0.25 mm.", fontsize=10, fontname="helv")

    # Page 5: Testing (TOC said Page 6 -> page drift!)
    p5 = doc.new_page(width=612, height=792)
    p5.insert_text((54, 70), "3. Testing", fontsize=14, fontname="helv")
    p5.insert_text((54, 100), "Vibration testing under 3600 RPM operation.", fontsize=10, fontname="helv")

    doc.save(str(path))
    doc.close()


def create_pdf_with_unresolved_cross_ref(path: Path):
    doc = pymupdf.open()
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((54, 70), "1. Scope", fontsize=14, fontname="helv")
    p1.insert_text((54, 100), "As illustrated in Fig. 5, the pressure vessel withstands 15 bar.", fontsize=10, fontname="helv")  # Fig. 5 does NOT exist!
    p1.insert_text((54, 130), "Refer to Table IV for fluid properties.", fontsize=10, fontname="helv")  # Table IV does NOT exist!
    p1.insert_text((54, 160), "2. Requirements", fontsize=14, fontname="helv")
    p1.insert_text((54, 190), "Maximum stress shall satisfy Eq. (9).", fontsize=10, fontname="helv")  # Eq. (9) does NOT exist!
    p1.insert_text((54, 220), "3. Testing", fontsize=14, fontname="helv")
    p1.insert_text((54, 250), "Testing according to standard specifications.", fontsize=10, fontname="helv")

    # Only Figure 1 exists!
    p1.draw_rect(pymupdf.Rect(54, 300, 250, 400), color=(0.2, 0.4, 0.8))
    p1.insert_text((54, 420), "Fig. 1. Actual schematic diagram.", fontsize=10, fontname="helv")

    doc.save(str(path))
    doc.close()


def create_pdf_with_duplicate_figures(path: Path):
    doc = pymupdf.open()
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((54, 70), "1. Scope", fontsize=14, fontname="helv")
    p1.draw_rect(pymupdf.Rect(54, 100, 250, 200), color=(0.2, 0.4, 0.8))
    p1.insert_text((54, 220), "Figure 1: Initial Motor Assembly", fontsize=10, fontname="helv")

    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((54, 70), "2. Requirements", fontsize=14, fontname="helv")
    p2.draw_rect(pymupdf.Rect(54, 100, 250, 200), color=(0.2, 0.4, 0.8))
    p2.insert_text((54, 220), "Figure 1: Secondary Stator Wiring", fontsize=10, fontname="helv")  # Duplicate Figure 1!

    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((54, 70), "3. Testing", fontsize=14, fontname="helv")
    doc.save(str(path))
    doc.close()


def create_corrupted_pdf(path: Path):
    # Completely invalid non-PDF binary junk
    with open(path, "wb") as f:
        f.write(b"\x00\xff\xfe\xfdINVALID_BINARY_CORRUPTED_STREAM_NOT_A_PDF\x00")


def create_multipage_docx(path: Path):
    doc = docx.Document()
    doc.add_heading("Section 1. Scope and Overview", level=1)
    doc.add_paragraph("This multi-page DOCX specification outlines thermal insulation standards.")
    doc.add_page_break()

    doc.add_heading("Section 2. Technical Requirements", level=1)
    doc.add_paragraph("Thermal conductivity must be less than 0.035 W/mK.")
    t = doc.add_table(rows=3, cols=3)
    for r_idx, row in enumerate(t.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.text = f"R{r_idx}C{c_idx}"
    doc.add_page_break()

    doc.add_heading("Section 3. Verification Testing", level=1)
    doc.add_paragraph("Perform ASTM C177 guarded hot plate thermal testing.")
    doc.save(str(path))


def generate_all_fixtures():
    create_1_page_pdf(FIXTURES_DIR / "test_1_page.pdf")
    create_n_page_pdf(FIXTURES_DIR / "test_20_page.pdf", 20)
    create_n_page_pdf(FIXTURES_DIR / "test_50_page.pdf", 50)
    create_n_page_pdf(FIXTURES_DIR / "test_100_page.pdf", 100)
    create_ieee_two_column_pdf(FIXTURES_DIR / "test_ieee_two_column.pdf")
    create_pdf_with_toc_and_drift(FIXTURES_DIR / "test_toc_drift.pdf")
    create_pdf_with_unresolved_cross_ref(FIXTURES_DIR / "test_unresolved_xref.pdf")
    create_pdf_with_duplicate_figures(FIXTURES_DIR / "test_duplicate_figures.pdf")
    create_corrupted_pdf(FIXTURES_DIR / "test_corrupted.pdf")
    create_multipage_docx(FIXTURES_DIR / "test_multipage.docx")


if __name__ == "__main__":
    generate_all_fixtures()
    print("All synthetic fixtures generated in:", FIXTURES_DIR)
