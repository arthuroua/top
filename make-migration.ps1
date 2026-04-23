param(
  [Parameter(Mandatory = $true)]
  [string]$Message
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repoRoot 'apps\api\scripts\create-migration.ps1'
powershell -ExecutionPolicy Bypass -File $scriptPath -Message $Message
