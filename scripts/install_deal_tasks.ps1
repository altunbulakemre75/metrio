# Firsat sayfasi zamanlanmis gorevleri.
#   - "Metrio Daily Scrape" (03:00 tarama) acilir; firsatlar taze fiyattan secilir.
#   - "Metrio Deals Post" her gun 12:30, 18:30, 21:00'de (TikTok'un yogun saatleri) python -m deals.run calistirir.
#   - "Metrio Deals Story" 15:00 "Bu indirim gercek mi?", "Metrio Deals Extra" 16:00 kozmetik disi turler.
#   - "Metrio Deals Stats" her gun 23:30'da takipci sayilarini kaydeder.
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
    New-ScheduledTaskTrigger -Daily -At '12:30'
    New-ScheduledTaskTrigger -Daily -At '18:30'
    New-ScheduledTaskTrigger -Daily -At '21:00'
)
# Kacirilan paylasim sonradan atilmaz: bilgisayar gec acilirsa iki gonderi ust uste dusmesin.
$settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings `
    -Description 'Firsat sayfasi: Instagram + Telegram kanali paylasimi (deals/run.py)' | Out-Null
Write-Output "${name}: 12:30, 18:30, 21:00 kuruldu"

# Gunluk takip: Telegram abone + Instagram takipci sayisi, ozet yonetici sohbetine (deals/stats.py).
$statsName = 'Metrio Deals Stats'
if (Get-ScheduledTask -TaskName $statsName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $statsName -Confirm:$false
}
$statsAction = New-ScheduledTaskAction -Execute $pythonw -Argument '-m deals.stats' -WorkingDirectory $root
Register-ScheduledTask -TaskName $statsName -Action $statsAction `
    -Trigger (New-ScheduledTaskTrigger -Daily -At '23:30') -Settings $settings `
    -Description 'Firsat sayfasi: gunluk takipci/abone takibi (deals/stats.py)' | Out-Null
Write-Output "${statsName}: her gun 23:30 kuruldu"

# Tek urunluk "Bu indirim gercek mi?" videosu (deals/story.py) ve kozmetik disi turlerin
# ayri Reels videosu (deals/run.py --extra). Ikisi de yonetici sohbetine gelir, elle paylasilir.
$extraTasks = @(
    @{ Name = 'Metrio Deals Story'; Args = '-m deals.story'; At = '15:00';
       Desc = 'Firsat sayfasi: "Bu indirim gercek mi?" videosu (deals/story.py)' },
    @{ Name = 'Metrio Deals Extra'; Args = '-m deals.run --extra'; At = '16:00';
       Desc = 'Firsat sayfasi: kozmetik disi turler icin ayri Reels (deals/run.py --extra)' }
)
foreach ($t in $extraTasks) {
    if (Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
    }
    $a = New-ScheduledTaskAction -Execute $pythonw -Argument $t.Args -WorkingDirectory $root
    Register-ScheduledTask -TaskName $t.Name -Action $a -Trigger (New-ScheduledTaskTrigger -Daily -At $t.At) `
        -Settings $settings -Description $t.Desc | Out-Null
    Write-Output "$($t.Name): her gun $($t.At) kuruldu"
}
