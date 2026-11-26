"""One explicit public artifact allowlist for Pages and the Windows demo."""
PUBLIC_FILES = (
    "index.html", "design-system.html", "styles/rollflow-design.css",
    "shared/schedule-core.js", "shared/schedule.css",
)
PUBLIC_ROUTES = frozenset({"/", *("/" + path for path in PUBLIC_FILES)})
