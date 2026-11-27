; Inno Setup 6 — versioned unsigned STAGING installations, no migration on setup.
#ifndef BundleDir
  #error "Supply BundleDir"
#endif
#ifdef Workstation
  #define AppName "RollFlow Staff Workstation (Staging)"
  #define AppCode "RollFlow.Workstation.5.0.0-rc.4.Staging"
  #define AppFolder "RollFlow-Workstation"
  #define SetupName "RollFlow-V5.0.0-rc.4-Workstation-x64-STAGING-Setup"
#else
  #define AppName "RollFlow Local School Lab (Staging)"
  #define AppCode "RollFlow.LocalLab.5.0.0-rc.4.Staging"
  #define AppFolder "RollFlow-LocalLab"
  #define SetupName "RollFlow-V5.0.0-rc.4-LocalLab-x64-STAGING-Setup"
#endif
[Setup]
AppId={#AppCode}
AppName={#AppName}
AppVersion=5.0.0-rc.4
AppPublisher=RollFlow
DefaultDirName={localappdata}\Programs\{#AppFolder}\5.0.0-rc.4
DefaultGroupName={#AppName} 5.0 RC4
DisableProgramGroupPage=yes
DisableDirPage=yes
UsePreviousAppDir=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputBaseFilename={#SetupName}
CloseApplications=no
RestartApplications=no
UninstallDisplayName={#AppName} 5.0 RC4
#ifdef Workstation
Uninstallable=yes
#else
; PostgreSQL instance.json can refer to the installed runtime. Never delete a
; runtime through an unattended uninstaller. ICT must retire it after review.
Uninstallable=no
#endif
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
#ifdef Workstation
Name: "{group}\Open school server"; Filename: "{app}\Open School Server.cmd"; WorkingDir: "{app}"
Name: "{group}\Configure approved server"; Filename: "{app}\Configure School Server.cmd"; WorkingDir: "{app}"
Name: "{group}\Connection diagnostics"; Filename: "{app}\School Connection Diagnostics.cmd"; WorkingDir: "{app}"
Name: "{userdesktop}\RollFlow School Server (Staging)"; Filename: "{app}\Open School Server.cmd"; WorkingDir: "{app}"; Tasks: desktopicon
#else
Name: "{group}\Protected local staging"; Filename: "{app}\Start RollFlow.cmd"; WorkingDir: "{app}"
Name: "{group}\Fictional training"; Filename: "{app}\Open Training Demo.cmd"; WorkingDir: "{app}"
Name: "{group}\Production readiness"; Filename: "{app}\Production Readiness.cmd"; WorkingDir: "{app}"
Name: "{group}\Pilot readiness"; Filename: "{app}\Pilot Readiness.cmd"; WorkingDir: "{app}"
Name: "{group}\Verify package"; Filename: "{app}\Verify Package.cmd"; WorkingDir: "{app}"
Name: "{userdesktop}\RollFlow Local Lab (Staging)"; Filename: "{app}\Start RollFlow.cmd"; WorkingDir: "{app}"; Tasks: desktopicon
#endif
[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\instance.json')) or DirExists(ExpandConstant('{app}\oneschool-imports')) then
    Result := 'This is a private data directory. Choose a new application directory.'
  else if FileExists(ExpandConstant('{app}\BUILD-INFO.json')) then
    Result := 'This version already exists. Keep it intact; install a new version or have ICT review retirement.';
end;
