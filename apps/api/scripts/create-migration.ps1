param(
  [Parameter(Mandatory = $true)]
  [string]$Message
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiRoot = Split-Path -Parent $scriptDir
Push-Location $apiRoot
try {
  python -m alembic revision --autogenerate -m $Message
}
finally {
  Pop-Location
}
