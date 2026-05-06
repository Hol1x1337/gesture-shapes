@echo off
REM Запуск Hand Gesture 3D Control приложения
echo ========================================
echo Hand Gesture 3D Control
echo ========================================
echo.
echo Запуск приложения...
echo.

cd src
python main.py

if errorlevel 1 (
    echo.
    echo Ошибка при запуске приложения!
    pause
)
