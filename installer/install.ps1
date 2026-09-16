<#
Instala o AlbionMercadoAmericas.exe (já gerado por build_exe.cmd) para o
usuário atual, sem precisar de administrador: copia para %LOCALAPPDATA%,
cria um atalho no Menu Iniciar e registra em "Aplicativos instalados" do
Windows para aparecer lá e poder desinstalar por lá também, além do
desinstalar.cmd. Não assina o executável digitalmente — assinatura de
código exige um certificado pago e verificação de identidade de empresa,
fora do que dá pra fazer aqui; o Windows pode avisar "editor desconhecido"
na primeira execução, o que é esperado e não indica um problema real.
#>
param(
    [string]$SourceExe = (Join-Path $PSScriptRoot "..\dist\AlbionMercadoAmericas.exe")
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SourceExe)) {
    Write-Error "Executável não encontrado em $SourceExe. Rode build_exe.cmd primeiro."
    exit 1
}

$installDir = Join-Path $env:LOCALAPPDATA "AlbionMercadoAmericas"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

$targetExe = Join-Path $installDir "AlbionMercadoAmericas.exe"
Copy-Item -Path $SourceExe -Destination $targetExe -Force

$uninstallScript = Join-Path $installDir "uninstall.ps1"
Copy-Item -Path (Join-Path $PSScriptRoot "uninstall.ps1") -Destination $uninstallScript -Force

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenu "Albion Mercado Americas.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetExe
$shortcut.WorkingDirectory = $installDir
$shortcut.Description = "Monitor de mercado e calculadoras para Albion Online (Américas)"
$shortcut.Save()

$versionPath = Join-Path $PSScriptRoot "..\VERSION"
$version = if (Test-Path $versionPath) { (Get-Content $versionPath -Raw).Trim() } else { "1.0.0" }

# HKCU (não HKLM): fica só para o usuário atual, sem precisar de admin.
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AlbionMercadoAmericas"
New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name "DisplayName" -Value "Albion Mercado Américas"
Set-ItemProperty -Path $uninstallKey -Name "DisplayVersion" -Value $version
Set-ItemProperty -Path $uninstallKey -Name "Publisher" -Value "italokaiq"
Set-ItemProperty -Path $uninstallKey -Name "DisplayIcon" -Value $targetExe
Set-ItemProperty -Path $uninstallKey -Name "InstallLocation" -Value $installDir
Set-ItemProperty -Path $uninstallKey -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$uninstallScript`""
Set-ItemProperty -Path $uninstallKey -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $uninstallKey -Name "NoRepair" -Value 1 -Type DWord
$sizeKb = [math]::Round((Get-Item $targetExe).Length / 1KB)
Set-ItemProperty -Path $uninstallKey -Name "EstimatedSize" -Value $sizeKb -Type DWord

Write-Host "Instalado em $targetExe"
Write-Host "Atalho criado em $shortcutPath"
Write-Host "Aparece em Configurações > Aplicativos > Aplicativos instalados como 'Albion Mercado Américas' — dá para desinstalar por lá também, além de desinstalar.cmd."
