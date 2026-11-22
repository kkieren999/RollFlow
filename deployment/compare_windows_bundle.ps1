<#
.SYNOPSIS
  Compare the source files inside a Windows RollFlow bundle with a GitHub branch.
.DESCRIPTION
  Read-only. Looks only at public source-code paths under the installation's
  app directory. Does not open databases, encrypted OneSchool archives, keys,
  logs, browser storage, or backups. No local files are uploaded.
  Requires internet access to query GitHub's public API.
.EXAMPLE
  powershell.exe -NoProfile -File .\deployment\compare_windows_bundle.ps1 -InstallPath "C:\RollFlow-V367"
.EXAMPLE
  powershell.exe -NoProfile -File .\deployment\compare_windows_bundle.ps1 -InstallPath "C:\RollFlow-V367" -ReportPath ".\rollflow-version-report.json"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallPath,

    [string]$Repository = 'kkieren999/RollFlow',

    [string]$Branch = 'feature/v3.6.7-unified-ui',

    [string]$ReportPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-GitBlobHash {
    param([Parameter(Mandatory = $true)][string]$FilePath)

    # Git's SHA-1 for a regular blob includes a header and NUL byte, not
    # just the file's SHA-1. This lets us compare to GitHub's tree entries.
    [byte[]]$fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
    [byte[]]$headerBytes = [System.Text.Encoding]::UTF8.GetBytes(
        'blob ' + [string]$fileBytes.Length
    )
    [byte[]]$blob = [byte[]]::new($headerBytes.Length + 1 + $fileBytes.Length)
    [System.Array]::Copy($headerBytes, 0, $blob, 0, $headerBytes.Length)
    $blob[$headerBytes.Length] = 0
    [System.Array]::Copy($fileBytes, 0, $blob, $headerBytes.Length + 1, $fileBytes.Length)

    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        return [System.BitConverter]::ToString($sha1.ComputeHash($blob)).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha1.Dispose()
    }
}

if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    throw 'Repository must be in owner/name form.'
}
if ($Branch -notmatch '^[A-Za-z0-9_./-]+$' -or $Branch.Contains('..')) {
    throw 'Invalid branch name.'
}

$installRoot = (Resolve-Path -LiteralPath $InstallPath).ProviderPath
$embeddedApp = Join-Path $installRoot 'app'
if (Test-Path -LiteralPath (Join-Path $embeddedApp 'index.html') -PathType Leaf) {
    $appPath = $embeddedApp
}
elseif (Test-Path -LiteralPath (Join-Path $installRoot 'index.html') -PathType Leaf) {
    $appPath = $installRoot
}
else {
    throw 'No RollFlow app/index.html or index.html found at that location. Supply the extracted Windows bundle folder.'
}

$headers = @{
    'Accept' = 'application/vnd.github+json'
    'User-Agent' = 'RollFlow-Source-Version-Check'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$base = "https://api.github.com/repos/$Repository"
try {
    $gitRef = Invoke-RestMethod -Uri "$base/git/ref/heads/$Branch" -Headers $headers -TimeoutSec 30
    $remoteCommit = [string]$gitRef.object.sha
    if ($remoteCommit -notmatch '^[0-9a-fA-F]{40}$') {
        throw 'GitHub returned no valid commit identifier.'
    }
    $remoteTree = Invoke-RestMethod -Uri "$base/git/trees/$remoteCommit?recursive=1" -Headers $headers -TimeoutSec 30
}
catch {
    throw "Could not read GitHub branch '$Branch'. Check internet access and GitHub API availability. $($_.Exception.Message)"
}
if ($remoteTree.truncated) {
    throw 'GitHub returned an incomplete file tree; refusing to report a match.'
}

$matchedCount = 0
$checkedCount = 0
$missing = New-Object 'System.Collections.Generic.List[string]'
$different = New-Object 'System.Collections.Generic.List[string]'

foreach ($entry in $remoteTree.tree) {
    if ($entry.type -ne 'blob') { continue }
    $relative = [string]$entry.path
    $isAppSource = ($relative -match '^(accounts|rollflow|templates|deployment)/') -or
        ($relative -in @('index.html', 'manage.py', 'requirements.txt', 'README.md'))
    if (-not $isAppSource) { continue }

    $checkedCount++
    $localFile = Join-Path $appPath ($relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path -LiteralPath $localFile -PathType Leaf)) {
        $missing.Add($relative)
        continue
    }

    $localHash = Get-GitBlobHash -FilePath $localFile
    if ($localHash -eq [string]$entry.sha) {
        $matchedCount++
    }
    else {
        $different.Add($relative)
    }
}

if ($checkedCount -eq 0) {
    throw 'No application files were returned from GitHub.'
}

$matches = $missing.Count -eq 0 -and $different.Count -eq 0
$report = [ordered]@{
    repository = $Repository
    branch = $Branch
    github_commit = $remoteCommit
    checked_app_folder = $appPath
    checked_utc = [DateTime]::UtcNow.ToString('o')
    files_checked = $checkedCount
    files_matching = $matchedCount
    files_missing = $missing.ToArray()
    files_different = $different.ToArray()
    source_matches_github = $matches
    note = 'Read-only source comparison. Does not verify database state, application behavior, GitHub Pages, or local extra files.'
}

Write-Host ""
Write-Host "RollFlow: Windows source vs GitHub"
Write-Host "GitHub branch: $Repository / $Branch"
Write-Host "GitHub commit: $remoteCommit"
Write-Host "Windows app folder: $appPath"
Write-Host "Matching files: $matchedCount / $checkedCount"
Write-Host "Missing files: $($missing.Count); differing files: $($different.Count)"
if ($matches) {
    Write-Host 'RESULT: source files match the selected GitHub commit.'
}
else {
    Write-Warning 'RESULT: Windows source differs from GitHub. Do not overwrite an existing installation; follow the backup-first upgrade guide.'
    foreach ($name in $missing) { Write-Host "MISSING: $name" }
    foreach ($name in $different) { Write-Host "DIFFERENT: $name" }
}
if ($ReportPath) {
    $json = $report | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText(
        [System.IO.Path]::GetFullPath($ReportPath),
        $json + [Environment]::NewLine,
        [System.Text.Encoding]::UTF8
    )
    Write-Host "Report written to: $ReportPath"
}
Write-Host 'No files, data, or installations were changed.'
if (-not $matches) { exit 2 }
