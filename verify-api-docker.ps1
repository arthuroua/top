param()

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

docker version *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker engine is not running. Start Docker Desktop and run this script again."
  exit 1
}

Push-Location $repoRoot
try {
  docker compose up --build -d db redis api
  docker compose logs api --tail 80
}
finally {
  Pop-Location
}
