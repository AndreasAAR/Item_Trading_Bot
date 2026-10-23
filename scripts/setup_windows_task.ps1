# PowerShell script to register local Windows Scheduled Task
param (
    [string]$Time = "09:00",
    [switch]$Uninstall
)

$TaskName = "TraderaMultiPlatformSync"
$ProjectDir = (Get-Item "$PSScriptRoot\..").FullName
$ScriptPath = "$ProjectDir\scripts\run_daily_sync.bat"

if ($Uninstall) {
    Write-Host "Unregistering scheduled task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task removed successfully." -ForegroundColor Green
    exit 0
}

Write-Host "Configuring Windows Scheduled Task: '$TaskName'..." -ForegroundColor Cyan
Write-Host "Project Directory: $ProjectDir"
Write-Host "Daily Execution Time: $Time"

$Action = New-ScheduledTaskAction -Execute "$ScriptPath" -WorkingDirectory "$ProjectDir"
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily background sync from Tradera to Blocket and Facebook Marketplace" `
    -Force | Out-Null

Write-Host "`n[SUCCESS] Task '$TaskName' is now registered and will run daily at $Time!" -ForegroundColor Green
Write-Host "Logs will be written to: $ProjectDir\data\sync_cron.log"
Write-Host "To test run immediately: Start-ScheduledTask -TaskName '$TaskName'"
