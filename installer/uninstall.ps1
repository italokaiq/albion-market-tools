<#
Remove o que install.ps1 criou: atalho do Menu Iniciar, entrada em
"Aplicativos instalados" e o executável. Por padrão MANTÉM seus dados
(mercado.sqlite3, histórico, receitas, perfis, preferências, logs) — são
arquivos de usuário, não do programa em si. Use -RemoveData para apagar
tudo junto, sem chance de recuperar.
#>
param(
    [switch]$RemoveData
)

$ErrorActionPreference = 'Stop'
$installDir = Join-Path $env:LOCALAPPDATA "AlbionMercadoAmericas"

Get-Process -Name "AlbionMercadoAmericas" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenu "Albion Mercado Americas.lnk"
if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force }

$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AlbionMercadoAmericas"
if (Test-Path $uninstallKey) { Remove-Item $uninstallKey -Recurse -Force }

if (Test-Path $installDir) {
    if ($RemoveData) {
        Remove-Item $installDir -Recurse -Force
        Write-Host "Programa e todos os dados removidos de $installDir."
    } else {
        foreach ($name in 'AlbionMercadoAmericas.exe', 'uninstall.ps1') {
            $path = Join-Path $installDir $name
            if (Test-Path $path) { Remove-Item $path -Force }
        }
        Write-Host "Programa removido. Seus dados (mercado.sqlite3, histórico, receitas, perfis) continuam em $installDir."
        Write-Host "Para apagar tudo também, rode este script de novo com -RemoveData."
    }
}
