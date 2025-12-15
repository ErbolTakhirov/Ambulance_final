@echo off
echo ========================================
echo   Перезапуск Ambulance Route Server
echo ========================================
echo.

REM Остановка всех процессов Python
echo Остановка старых процессов...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Запуск сервера
echo.
echo ========================================
echo   Запуск сервера...
echo ========================================
echo.
python manage.py runserver

pause
