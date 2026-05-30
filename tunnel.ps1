# ============================================================
#  Cloudflare Quick Tunnel - Enterprise LLM Wiki
#  Frontend (3000) + Backend (8080)
#  Usage: .\tunnel.ps1
# ============================================================

$backendLog  = "$env:TEMP\cf_llmwiki_backend.log"
$frontendLog = "$env:TEMP\cf_llmwiki_frontend.log"

# Clear old log files
if (Test-Path $backendLog)  { Remove-Item $backendLog  -Force }
if (Test-Path $frontendLog) { Remove-Item $frontendLog -Force }

Write-Host ""
Write-Host "Starting Cloudflare tunnels (Enterprise LLM Wiki)..." -ForegroundColor Cyan

# ---- Helper: wait for tunnel URL to appear in log file ----
function Wait-TunnelUrl {
    param([string]$LogFile, [string]$Label)
    $url   = $null
    $tries = 0
    while (-not $url -and $tries -lt 20) {
        Start-Sleep -Seconds 2
        $tries++
        if (Test-Path $LogFile) {
            $content = Get-Content $LogFile -Raw -ErrorAction SilentlyContinue
            if ($content) {
                $m = [regex]::Match($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
                if ($m.Success) { $url = $m.Value }
            }
        }
    }
    return $url
}

# ---- Start backend tunnel (port 8080) ----
Write-Host "Backend  tunnel starting (port 8080)..." -ForegroundColor Yellow

$backendProc = Start-Process `
    -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:8080" `
    -RedirectStandardError $backendLog `
    -NoNewWindow `
    -PassThru

$backendUrl = Wait-TunnelUrl -LogFile $backendLog -Label "Backend"

if ($backendUrl) {
    Write-Host "Backend  ready: $backendUrl" -ForegroundColor Green
} else {
    Write-Host "Backend  URL not detected - check $backendLog" -ForegroundColor Red
}

# ---- Update backend ALLOW_ORIGINS to accept trycloudflare.com ----
$backendEnvPath = Join-Path $PSScriptRoot "backend\.env"
if (Test-Path $backendEnvPath) {
    $lines = Get-Content $backendEnvPath | Where-Object { $_ -notmatch "^ALLOW_ORIGINS=" }
    $lines += "ALLOW_ORIGINS=*"
    Set-Content $backendEnvPath $lines -Encoding utf8
    Write-Host "Updated  backend\.env  ->  ALLOW_ORIGINS=*" -ForegroundColor Cyan
}

# ---- Restart backend with new CORS config ----
Write-Host "Restarting backend (port 8080)..." -ForegroundColor Yellow

# Kill existing process on port 8080
$pid8080 = (netstat -ano | Select-String ":8080\s.*LISTENING") -replace ".*\s+(\d+)$", '$1' | Select-Object -First 1
if ($pid8080 -and $pid8080 -match '^\d+$') {
    Stop-Process -Id ([int]$pid8080) -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "Killed old backend process (PID $pid8080)" -ForegroundColor Gray
}

$backendDir = Join-Path $PSScriptRoot "backend"
Start-Process -FilePath "powershell" `
    -ArgumentList "-NoProfile", "-Command",
        "cd '$backendDir'; .venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8080" `
    -WindowStyle Minimized

Start-Sleep -Seconds 5
Write-Host "Backend  restarted" -ForegroundColor Green

# ---- Start frontend tunnel (port 3000) ----
Write-Host "Frontend tunnel starting (port 3000)..." -ForegroundColor Yellow

$frontendProc = Start-Process `
    -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:3000" `
    -RedirectStandardError $frontendLog `
    -NoNewWindow `
    -PassThru

$frontendUrl = Wait-TunnelUrl -LogFile $frontendLog -Label "Frontend"

if ($frontendUrl) {
    Write-Host "Frontend ready: $frontendUrl" -ForegroundColor Green
} else {
    Write-Host "Frontend URL not detected - check $frontendLog" -ForegroundColor Red
}

# ---- Summary ----
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnels Ready" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
if ($frontendUrl) { Write-Host "  App      : $frontendUrl"      -ForegroundColor Green }
if ($backendUrl)  {
    Write-Host "  API      : $backendUrl"      -ForegroundColor Green
    Write-Host "  API Docs : $backendUrl/docs" -ForegroundColor Green
}
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Start (or restart) Next.js with tunnel mode:" -ForegroundColor Yellow
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run dev:tunnel" -ForegroundColor Green
Write-Host ""
Write-Host "  (uses --hostname 0.0.0.0 so Next.js accepts Cloudflare Host headers)" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop all tunnels." -ForegroundColor Gray

# ---- Keep alive until Ctrl+C ----
try {
    while ($true) { Start-Sleep -Seconds 30 }
} finally {
    Write-Host ""
    Write-Host "Stopping tunnels..." -ForegroundColor Red
    if ($backendProc  -and -not $backendProc.HasExited)  { Stop-Process -Id $backendProc.Id  -Force -ErrorAction SilentlyContinue }
    if ($frontendProc -and -not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Done." -ForegroundColor Gray
}
