"""One entry point for the complete website; explicit, separate protected mode."""
from pathlib import Path

EXISTING = r"%LOCALAPPDATA%\RollFlow-V3641-Staging"
FRESH = r"%LOCALAPPDATA%\RollFlow-V38-Fresh-Staging"


def launcher_text(state, command, options=""):
    return (
        '@echo off\nsetlocal\n'
        '"%~dp0python\\python.exe" -m deployment.native --state "' + state + '" ' +
        command + options + ' %*\n'
        'if errorlevel 1 pause\n'
    )


def write_launchers(out: Path):
    website = (
        '@echo off\nsetlocal\n'
        'title RollFlow - School Management System (fictional workspace)\n'
        '"%~dp0python\\python.exe" -m deployment.training\n'
        'if errorlevel 1 pause\n'
    )
    for name in ("Open Training Demo.cmd",):
        (out / name).write_text(website, encoding="ascii")
    commands = {
        "First Setup Fresh.cmd": (FRESH, "init", " --db-port 55438 --web-port 18087"),
        "Start Fresh Protected.cmd": (FRESH, "start", ""),
        "Upgrade Fresh Protected.cmd": (FRESH, "upgrade", ""),
        "Manage Fresh Protected.cmd": (FRESH, "manage", ""),
        "Snapshot Fresh Protected.cmd": (FRESH, "snapshot", ""),
        "Diagnose Fresh Protected.cmd": (FRESH, "diagnostics", ""),
        "Snapshot Existing Protected.cmd": (EXISTING, "snapshot", ""),
        "Diagnose Existing Protected.cmd": (EXISTING, "diagnostics", ""),
        "Backup Fresh Protected.cmd": (FRESH, "backup", ""),
        "Start Existing Protected.cmd": (EXISTING, "start", ""),
        "Upgrade Existing.cmd": (EXISTING, "upgrade", ""),
        "Manage RollFlow.cmd": (EXISTING, "manage", ""),
        "Backup RollFlow.cmd": (EXISTING, "backup", ""),
    }
    # Retain the old setup name, but explicitly initialise a fresh database.
    commands["First Setup.cmd"] = commands["First Setup Fresh.cmd"]
    for name, (state, command, options) in commands.items():
        (out / name).write_text(launcher_text(state, command, options), encoding="ascii")
    (out / "Protected Workspace.cmd").write_text(
        '@echo off\nsetlocal\n:menu\n'
        'cls\n'
        'echo RollFlow - protected database-backed STAGING workspace\n'
        'echo Not yet equivalent to the full fictional website interface.\n'
        'echo 1. Initialise a new isolated test database (one time only)\n'
        'echo 2. Start the new isolated test database - http://localhost:18087/\n'
        'echo 3. Back up and upgrade the existing V3.6/V3.7 database\n'
        'echo 4. Start the existing database - http://localhost:18085/\n'
        'echo 5. Back up and upgrade the fresh test database\n'
        'echo 6. Open the full fictional website workspace instead\n'
        'echo Q. Quit\n'
        'choice /C 123456Q /N /M "Choose: "\n'
        'if errorlevel 7 exit /b 0\n'
        'if errorlevel 6 (call "%~dp0Open Training Demo.cmd" & goto menu)\n'
        'if errorlevel 5 (call "%~dp0Upgrade Fresh Protected.cmd" & goto menu)\n'
        'if errorlevel 4 (call "%~dp0Start Existing Protected.cmd" & goto menu)\n'
        'if errorlevel 3 (call "%~dp0Upgrade Existing.cmd" & goto menu)\n'
        'if errorlevel 2 (call "%~dp0Start Fresh Protected.cmd" & goto menu)\n'
        'if errorlevel 1 (call "%~dp0First Setup Fresh.cmd" & goto menu)\n'
        'exit /b 1\n', encoding="ascii")

    (out / "Start RollFlow.cmd").write_text('@echo off\ncall "%~dp0Protected Workspace.cmd"\n', encoding="ascii")
