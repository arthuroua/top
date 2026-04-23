param()

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiRoot = Join-Path $repoRoot 'apps\api'
$pythonSnippet = @"
from app.db import init_db
init_db()
print({"status": "ok"})
"@

Push-Location $apiRoot
try {
  $pythonSnippet | python -
}
finally {
  Pop-Location
}
