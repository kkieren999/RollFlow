"""OneSchool's actual TTLineAlignmentExport workbook layout (one file per line).

Only trusted administrator review can activate extracted data. Staff codes in
these files are *not* OneSchool Staff_Id login credentials and MUST NOT be
used for authorisation or guessed Django teacher account creation.
"""
import hashlib
import re

GROUP = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday)\s*-\s*PERIOD\s*([1-4])$", re.I)
SECTION = re.compile(r"^Year\s+(7|8|9|10|11|12)\s*-\s*Line\s+([1-7])$", re.I)
OFFLINE = re.compile(r"^Year\s+(7|8|9|10|11|12)\s*-\s*OFFLINE$", re.I)
CODE = re.compile(r"^[A-Z0-9_-]{1,30}$")
STAFF = re.compile(r"^[A-Z0-9_-]{0,40}$")
WEEKDAYS = {"monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5}
REQUIRED_LINES = set(range(1, 8))
MAX_ROWS = 600


def parse_alignment_file(raw):
    from .oneschool_documents import workbook_from_bytes
    wb = workbook_from_bytes(raw)
    try:
        if "Sheet1" not in wb.sheetnames or "ReportCriteria" not in wb.sheetnames:
            raise ValueError("Expected the Sheet1 and ReportCriteria worksheets.")
        ws, criteria = wb["Sheet1"], wb["ReportCriteria"]
        if ws.max_row > MAX_ROWS or ws.max_column > 9 or criteria.max_row > 30:
            raise ValueError("TTLineAlignmentExport workbook dimensions exceed safe limits.")
        details = {str(row[0]).strip(): row[1] for row in
                   criteria.iter_rows(min_row=1, max_col=2, values_only=True)
                   if row[0] is not None}
        if str(details.get("Report", "")).strip() != "TTLineAlignmentExport":
            raise ValueError("ReportCriteria must identify TTLineAlignmentExport.")
        try:
            line_no = int(details["LineNr"])
            version_id = str(int(details["TimetableVersionId"]))
            claimed_count = int(details["Record Count"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Missing or invalid OneSchool line/record/version criteria.") from None
        if line_no not in REQUIRED_LINES or not version_id or claimed_count < 0:
            raise ValueError("Unrecognised OneSchool timetable line or record count.")
        raw_rows = list(ws.iter_rows(min_row=1, max_col=9, values_only=True))
        if len(raw_rows) < 3:
            raise ValueError("TTLineAlignmentExport has no day-period blocks.")
        headers, labels, data = raw_rows[0], raw_rows[1], raw_rows[2:]
        groups = []
        for col in range(0, 9, 3):
            head = headers[col]
            if head is None:
                if any(x is not None for x in headers[col:col+3]):
                    raise ValueError("Unexpected day/period header position.")
                continue
            match = GROUP.fullmatch(str(head).strip())
            if not match:
                raise ValueError("Expected day and PERIOD heading in groups of three columns.")
            if tuple(str(x or "").strip() for x in labels[col:col+3]) != ("Class", "Teacher", "Room"):
                raise ValueError("Expected Class, Teacher, Room columns in every day/period block.")
            day = WEEKDAYS[match.group(1).lower()]
            period = int(match.group(2))
            groups.append((col, day, period))
        if not groups:
            raise ValueError("No timetable blocks in alignment export.")
        if len(set((day, period) for _, day, period in groups)) != len(groups):
            raise ValueError("Duplicate day/period heading.")
        year = None
        records = []
        offline_rows = 0
        for row_no, row in enumerate(data, 3):
            first = str(row[0]).strip() if row[0] is not None else ""
            section = SECTION.fullmatch(first)
            if section:
                if int(section.group(2)) != line_no:
                    raise ValueError(f"Row {row_no}: section belongs to a different timetable line.")
                year = int(section.group(1))
                continue
            if OFFLINE.fullmatch(first):
                offline_rows += 1
                continue
            if all(x is None or str(x).strip() == "" for x in row):
                continue
            if year is None:
                raise ValueError(f"Row {row_no}: class appears before a year/line section.")
            for col, day, period in groups:
                klass = str(row[col] or "").strip().upper()
                teacher = str(row[col+1] or "").strip().upper()
                room = str(row[col+2] or "").strip().upper()
                if not klass:
                    if teacher or room:
                        raise ValueError(f"Row {row_no}: teacher/room without a class code.")
                    continue
                if not CODE.fullmatch(klass):
                    raise ValueError(f"Row {row_no}: invalid class code.")
                if not STAFF.fullmatch(teacher) or not STAFF.fullmatch(room):
                    raise ValueError(f"Row {row_no}: invalid staff/room code.")
                records.append({
                    "line_number": line_no, "year_level": year,
                    "weekday": day, "period": period, "class_code": klass,
                    "staff_code": teacher, "room_code": room,
                })
        if len(records) != claimed_count:
            raise ValueError(f"TTLine count mismatch: expected {claimed_count}, parsed {len(records)}.")
        return records, {
            "line_number": line_no,
            "timetable_version_id": version_id,
            "allocations": len(records),
            "offline_rows": offline_rows,
            "unallocated_staff": sum(not r["staff_code"] for r in records),
            "unallocated_room": sum(not r["room_code"] for r in records),
            "day_period_blocks": len(groups),
            "format": "TTLineAlignmentExport",
        }
    finally:
        wb.close()


def parse_alignment_batch(files):
    """files: [(filename, original_bytes)] ; validates all seven parts together."""
    lines, rows, digest = set(), [], hashlib.sha256()
    version = None
    for name, raw in files:
        if not name.lower().endswith(".xlsx"):
            raise ValueError("Only the original TTLineAlignmentExport XLSX files can be activated.")
        extracted, meta = parse_alignment_file(raw)
        line = meta["line_number"]
        if line in lines:
            raise ValueError("An alignment line number appears in more than one file.")
        if version is not None and meta["timetable_version_id"] != version:
            raise ValueError("TTLine files must all come from the same OneSchool timetable version.")
        lines.add(line)
        version = meta["timetable_version_id"]
        rows.extend(extracted)
        digest.update(hashlib.sha256(raw).digest())
    keys = [(v["weekday"], v["period"], v["class_code"]) for v in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("A class occurs twice in the same day/period across line files.")
    missing = sorted(REQUIRED_LINES - lines)
    return rows, {
        "lines": sorted(lines),
        "missing_lines": missing,
        "complete": not missing,
        "timetable_version_id": version,
        "allocation_count": len(rows),
        "distinct_classes": len({v["class_code"] for v in rows}),
        "staff_codes": len({v["staff_code"] for v in rows if v["staff_code"]}),
        "rooms": len({v["room_code"] for v in rows if v["room_code"]}),
        "unallocated_staff": sum(not r["staff_code"] for r in rows),
        "source_signature": digest.hexdigest(),
    }
