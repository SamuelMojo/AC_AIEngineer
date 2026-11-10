param(
    [string]$InstanceId = "i-043e5c2277277e267"
)

# 1. Check and start Ollama if needed
Write-Host "Checking if Ollama is running..." -ForegroundColor Cyan
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue

if (-not $ollamaRunning) {
    Write-Host "Ollama is not running. Starting Ollama server in background..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "ollama serve"
    Start-Sleep -Seconds 5 # Give the server a few seconds to spin up
} else {
    Write-Host "Ollama is already running." -ForegroundColor Green
}

# 2. Start AWS EC2 instance
Write-Host "Starting AWS EC2 instance ($InstanceId)..." -ForegroundColor Cyan
aws ec2 start-instances --instance-ids $InstanceId | Out-Null

Write-Host "Waiting for EC2 instance to initialize..." -ForegroundColor Cyan
aws ec2 wait instance-running --instance-ids $InstanceId

# 3. Launch background S3 sync watcher
Write-Host "Launching background S3 sync watcher..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python sync_outputs_v2.py"

# 4. Start training (assetto_corsa_gym lives in the submodule; run it from the repo root so
#    outputs\ and this repo's config.yml are used)
Write-Host "Starting training (external\assetto_corsa_gym\train.py)..." -ForegroundColor Green
$Upstream = Join-Path $PSScriptRoot "external\assetto_corsa_gym"
$env:PYTHONPATH = "$Upstream;$Upstream\assetto_corsa_gym;$Upstream\algorithm\discor"
Set-Location $PSScriptRoot
python "$Upstream\train.py" --config config.yml
