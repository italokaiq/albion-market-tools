@echo off
cd /d "%~dp0"
echo Isso remove o atalho, o registro em Aplicativos instalados e o executavel.
echo Seus dados (mercado.sqlite3, historico, receitas, perfis) NAO sao apagados por padrao.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "installer\uninstall.ps1"
pause
