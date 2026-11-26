"""Read-only presentation projection of server-authorised schedule rows."""
def project_days(days):
    return {
        "version": 1,
        "days": [
            {"date": day["date"].isoformat(), "lessons": [
                {"date": day["date"].isoformat(), "code": row["code"],
                 "title": row["name"], "period": str(row["period_label"]),
                 "time": row["start"] + "–" + row["end"],
                 "room": row.get("room") or "", "assignment": ""}
                for row in day["rows"]]}
            for day in days
        ],
    }
