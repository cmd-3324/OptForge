#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Aumid   # optional: clear only this sender; empty = all
)

$ErrorActionPreference = 'Stop'

try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
} catch {
    Write-Error "WinRT notification API unavailable (not Windows 10/11?)"
    exit 2
}

$history = [Windows.UI.Notifications.ToastNotificationManager]::History

if ($Aumid) {
    $targets = @($Aumid)
} else {
    $key = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings'
    if (-not (Test-Path $key)) {
        Write-Output 0
        exit 0
    }

    $targets = @(
        Get-ChildItem -Path $key -ErrorAction Stop |
            ForEach-Object { $_.PSChildName }
    )
}

$cleared = 0
foreach ($target in $targets) {
    if ([string]::IsNullOrWhiteSpace($target)) {
        continue
    }

    try {
        $items = $history.GetHistory($target)
        if (@($items).Count -eq 0) {
            continue
        }

        $history.Clear($target)
        $cleared++
    } catch {
        Write-Warning "Could not clear notifications for '$target': $($_.Exception.Message)"
    }
}

Write-Output $cleared
