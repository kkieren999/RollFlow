"""Read structured *legend evidence* from OneSchool's staff timetable PDF.

No teacher name is retained in parsed metadata. Staff codes in the PDF are
not OneSchool Staff_Id and are never used as account authorization. This
parser does not attempt to recover exact lesson cells from the rendered PDF;
the seven TTLine XLSX exports are the authoritative weekly period source.
"""
import io
import re
from pypdf import PdfReader

STAFF_CODE = re.compile(r"^[A-Z0-9_-]{3,40}$")
CLASS_CODE = re.compile(r"^[A-Z0-9_-]{3,30}$")
VERSION = re.compile(r"TTStaffTimetable\s*-\s*V\d+\.\d+\s*-\s*\d+\s*-\s*(\d{3,12})\s*-")
LINE = re.compile(r"^Line\s*([1-7])?$", re.I)
# OneSchool prints this timestamp immediately after the legend table.
FOOTER_DATE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"[A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM)$",
    re.I,
)


def is_footer_start(line):
    return bool(FOOTER_DATE.fullmatch(line) or VERSION.search(line))



def parse_staff_pdf(raw):
    if not raw.startswith(b"%PDF-"):
        raise ValueError("This is not a PDF source.")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Password-protected OneSchool PDFs cannot be parsed.")
        if len(reader.pages) == 0 or len(reader.pages) > 200:
            raise ValueError("Expected a staff timetable of 1–200 pages.")
        version_id = None
        refs = {}
        staff = set()
        unreadable_legends = 0
        for page_no, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            lines = [x.strip() for x in text.splitlines() if x.strip()]
            if not lines or not STAFF_CODE.fullmatch(lines[0]):
                raise ValueError(f"Page {page_no}: staff code could not be read.")
            staff_code = lines[0].upper()
            staff.add(staff_code)
            found = VERSION.search(text)
            if not found:
                raise ValueError(f"Page {page_no}: OneSchool timetable version footer missing.")
            if version_id is not None and found.group(1) != version_id:
                raise ValueError("Staff timetable PDF contains inconsistent timetable versions.")
            version_id = found.group(1)
            if "Legend:" not in lines:
                # Some staff have no classes; the source PDF can omit a legend.
                unreadable_legends += 1
                continue
            begin = lines.index("Legend:")
            tail = lines[begin+1:]
            # When no classes are allocated OneSchool prints only the first
            # two column headings, followed immediately by the report footer.
            # Do not mistake a damaged two-column nonempty table for an empty one.
            if (tail[:2] == ["Class Code", "Class Name"]
                    and len(tail) >= 3 and is_footer_start(tail[2])):
                unreadable_legends += 1
                continue
            if tail[:3] != ["Class Code", "Class Name", "Line"]:
                raise ValueError(f"Page {page_no}: unexpected timetable legend headings.")
            end = next((index for index, value in enumerate(tail[3:], 3)
                        if is_footer_start(value)), None)
            if end is None or (end - 3) % 3:
                raise ValueError(f"Page {page_no}: malformed class legend or missing footer.")
            if end == 3:
                unreadable_legends += 1
                continue
            for col in range(3, end, 3):
                class_code, subject, label = tail[col:col+3]
                if not CLASS_CODE.fullmatch(class_code):
                    raise ValueError(f"Page {page_no}: invalid class code in legend.")
                match = LINE.fullmatch(label)
                if match is None or len(subject) > 100:
                    raise ValueError(f"Page {page_no}: malformed class legend.")
                line_number = int(match.group(1)) if match.group(1) else None
                key = (staff_code, class_code)
                record = {
                    "staff_code": staff_code, "class_code": class_code,
                    "subject_name": subject, "line_number": line_number,
                }
                if key in refs and refs[key] != record:
                    raise ValueError(f"Page {page_no}: contradictory staff class evidence.")
                refs[key] = record
        if not refs:
            raise ValueError("No class legend entries were found in this staff PDF.")
        return list(refs.values()), {
            "pages": len(reader.pages),
            "staff_codes": len(staff),
            "staff_class_references": len(refs),
            "distinct_classes": len({v["class_code"] for v in refs.values()}),
            "pages_without_legend": unreadable_legends,
            "timetable_version_id": version_id,
            "staff_names_saved": False,
            "permission_grants": False,
        }
    except ValueError:
        raise
    except Exception:
        raise ValueError("Unable to extract reliable staff timetable legends.") from None
