$ram = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB
$disks = Get-PhysicalDisk | Select-Object FriendlyName, MediaType, @{N='SizeGB';E={[math]::Round($_.Size/1GB, 2)}}
Write-Host "--- SYSTEM REPORT ---"
Write-Host "Total RAM: $ram GB"
Write-Host "Disks:"
$disks | Format-Table -AutoSize
