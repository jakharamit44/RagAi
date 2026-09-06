@echo off
setlocal
echo ==========================================================================
echo        ENTERPRISE UNIVERSITY RAG PLATFORM - WINDOWS LAUNCHER
echo ==========================================================================
echo.
echo Executing PowerShell setup wizard with bypass execution policy...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup script exited with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)
echo.
pause
