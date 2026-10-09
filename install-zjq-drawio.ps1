param([string]$SkillRoot, [string]$DrawioPath)
$ErrorActionPreference = 'Stop'
$CodexProfileRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
if (-not $SkillRoot) { $SkillRoot = Join-Path $CodexProfileRoot 'skills' }
$SkillRoot = [IO.Path]::GetFullPath($SkillRoot)
$Names = @('zjq-drawio', 'zjq-drawio-tools')
foreach ($Name in $Names) {
  $Source = Join-Path (Join-Path $PSScriptRoot 'skills') $Name
  if (-not (Test-Path -LiteralPath (Join-Path $Source 'SKILL.md'))) { throw ('Missing source skill: ' + $Name) }
  $Target = Join-Path $SkillRoot $Name
  if (Test-Path -LiteralPath $Target) { throw ('Existing skill retained; install stopped: ' + $Target) }
}
if ($DrawioPath) {
  $DrawioPath = (Resolve-Path -LiteralPath $DrawioPath).Path
}
New-Item -ItemType Directory -Path $SkillRoot -Force | Out-Null
$SkipDirs = @('__pycache__', '.zjq-drawio', 'evidence', 'profiles', 'working-copies', 'demo-output', 'launcher-logs', 'outputs', 'private-tests')
foreach ($Name in $Names) {
  $Source = Join-Path (Join-Path $PSScriptRoot 'skills') $Name
  $Target = Join-Path $SkillRoot $Name
  foreach ($File in (Get-ChildItem -LiteralPath $Source -Recurse -File -Force)) {
    $Relative = $File.FullName.Substring($Source.Length).TrimStart('\', '/')
    $Segments = $Relative -split '[\\/]'
    if (($Segments | Where-Object { $SkipDirs -contains $_ }).Count -gt 0 -or $File.Extension -in @('.pyc', '.pyo') -or $File.Name.EndsWith('.report.json')) { continue }
    $Output = Join-Path $Target $Relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $Output) -Force | Out-Null
    Copy-Item -LiteralPath $File.FullName -Destination $Output
  }
  Write-Output ('Installed: ' + $Target)
}
if ($DrawioPath) {
  $ConfigFolder = Join-Path $CodexProfileRoot 'zjq-drawio'
  $ConfigPath = Join-Path $ConfigFolder 'config.json'
  $Config = if (Test-Path -LiteralPath $ConfigPath) { Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{} }
  $Config | Add-Member -NotePropertyName drawioPath -NotePropertyValue $DrawioPath -Force
  New-Item -ItemType Directory -Path $ConfigFolder -Force | Out-Null
  $Utf8 = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($ConfigPath, ($Config | ConvertTo-Json -Depth 10), $Utf8)
  Write-Output ('Local configuration: ' + $ConfigPath)
}
Write-Output 'Open a new Codex conversation to discover the two ZJQ skills.'
