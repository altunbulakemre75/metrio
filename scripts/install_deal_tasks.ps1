# Firsat sayfasi zamanlanmis gorevleri.
#   - "Metrio Daily Scrape" (03:00 tarama) acilir; firsatlar taze fiyattan secilir.
#   - "Metrio Deals Post" her gun 10:00, 14:00, 19:00'da python -m deals.run calistirir.
#   - "Metrio Deals Stats" her gun 21:30'da takipci sayilarini kaydeder.
# Calistirma:  powershell -ExecutionPolicy Bypass -File scripts\install_deal_tasks.ps1
# Yol "Yeni klasor" icindeki o harfi yuzunden .bat kullanilmiyor; pythonw.exe dogrudan cagriliyor.

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $pythonw)) { throw "pythonw.exe bulunamadi: $pythonw" }

$scrape = Get-ScheduledTask -TaskName 'Metrio Daily Scrape' -ErrorAction SilentlyContinue
if ($scrape) {
    Enable-ScheduledTask -TaskName 'Metrio Daily Scrape' | Out-Null
    Write-Output 'Metrio Daily Scrape: acildi'
} else {
    Write-Output 'Metrio Daily Scrape bulunamadi; once tarama gorevini kurun.'
}

$name = 'Metrio Deals Post'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument '-m deals.run' -WorkingDirectory $root
$triggers = @(
    New-ScheduledTaskTrigger -Daily -At '10:00'
    New-ScheduledTaskTrigger -Daily -At '14:00'
    New-ScheduledTaskTrigger -Daily -At '19:00'
)
# Kacirilan paylasim sonradan atilmaz: bilgisayar gec acilirsa iki gonderi ust uste dusmesin.
$settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings `
    -Description 'Firsat sayfasi: Instagram + Telegram kanali paylasimi (deals/run.py)' | Out-Null
Write-Output "${name}: 10:00, 14:00, 19:00 kuruldu"

# Gunluk takip: Telegram abone + Instagram takipci sayisi, ozet yonetici sohbetine (deals/stats.py).
$statsName = 'Metrio Deals Stats'
if (Get-ScheduledTask -TaskName $statsName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $statsName -Confirm:$false
}
$statsAction = New-ScheduledTaskAction -Execute $pythonw -Argument '-m deals.stats' -WorkingDirectory $root
Register-ScheduledTask -TaskName $statsName -Action $statsAction `
    -Trigger (New-ScheduledTaskTrigger -Daily -At '21:30') -Settings $settings `
    -Description 'Firsat sayfasi: gunluk takipci/abone takibi (deals/stats.py)' | Out-Null
Write-Output "${statsName}: her gun 21:30 kuruldu"
