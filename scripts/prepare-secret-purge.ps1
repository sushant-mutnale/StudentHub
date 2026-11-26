param(
    [switch]$DryRun,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

if ($DryRun -and $Apply) {
    throw "Cannot combine -DryRun and -Apply. Choose one."
}

if ($DryRun -or -not $Apply) {
    "Dry run: git filter-repo --invert-paths --path backend/.env.production"
    exit 0
}

if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    throw "git-filter-repo is required. Install it before running this script."
}

git filter-repo --invert-paths --path backend/.env.production
if ($LASTEXITCODE -ne 0) {
    throw "git-filter-repo failed with exit code $LASTEXITCODE"
}

$tracked = git ls-files backend/.env.production
if ($tracked) {
    throw "backend/.env.production is still tracked after purge"
}

"Local history purge prepared. Do not force-push without explicit approval."
