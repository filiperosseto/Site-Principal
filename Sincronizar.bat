@echo off
cd /d "%~dp0"
echo ==========================================
echo   Sincronizando com o GitHub...
echo ==========================================

git add .

set /p mensagem="Digite uma mensagem para o commit: "
git commit -m "%mensagem%"

git push origin main

echo ==========================================
echo   Sincronizacao concluida!
echo ==========================================
pause