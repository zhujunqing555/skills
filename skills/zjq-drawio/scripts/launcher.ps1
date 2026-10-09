param([string]$InputPath, [string]$WorkDir, [ValidateSet('open', 'demo')][string]$Mode = 'open')
$ErrorActionPreference = 'Stop'
$NodeRuntimePath = (Get-Command node -ErrorAction Stop).Source
$LiveScriptPath = Join-Path $PSScriptRoot 'live.mjs'
if (-not $WorkDir) { $WorkDir = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ZJQ_drawio' }
$WorkDir = [IO.Path]::GetFullPath($WorkDir)
$LogFolder = Join-Path $WorkDir 'launcher-logs'
New-Item -ItemType Directory -Path $LogFolder -Force | Out-Null
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$OutLog = Join-Path $LogFolder ($Stamp + '.out.txt')
$ErrorLog = Join-Path $LogFolder ($Stamp + '.err.txt')
if ($WorkDir.Contains('"') -or $LiveScriptPath.Contains('"')) { throw 'Invalid path quotation.' }
$NodeArgs = @('"' + $LiveScriptPath + '"', $Mode, '--hold', '--workdir', '"' + $WorkDir + '"')
if ($InputPath) {
  $InputPath = (Resolve-Path -LiteralPath $InputPath).Path
  if ($InputPath.Contains('"')) { throw 'Invalid input path quotation.' }
  $NodeArgs += @('--input', '"' + $InputPath + '"')
}
$Helper = Start-Process -FilePath $NodeRuntimePath -ArgumentList $NodeArgs -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrorLog -PassThru
Write-Output ('Background helper PID: ' + $Helper.Id)
Write-Output ('Status log: ' + $OutLog)
Write-Output ('Error log: ' + $ErrorLog)
Write-Output 'The helper exits after its controlled draw.io window closes.'
