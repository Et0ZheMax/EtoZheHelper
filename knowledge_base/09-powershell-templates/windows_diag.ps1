$OutDir = Join-Path $env:TEMP ("diag-" + $env:COMPUTERNAME + "-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

hostname | Out-File "$OutDir\hostname.txt"
whoami /all | Out-File "$OutDir\whoami-all.txt"
ipconfig /all | Out-File "$OutDir\ipconfig-all.txt"
route print | Out-File "$OutDir\routes.txt"
gpresult /r | Out-File "$OutDir\gpresult.txt"
net use | Out-File "$OutDir\net-use.txt"
Get-Service | Sort-Object Status,Name | Out-File "$OutDir\services.txt"
Get-EventLog -LogName System -Newest 200 | Out-File "$OutDir\system-events.txt"

Write-Host "Diagnostics saved to $OutDir"
