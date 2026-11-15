@echo off
setlocal
cd /d "%~dp0"

:: ===========================================================================
::  JARVIS - one click silent auto-start installer
::  - copies a shortcut to start_jarvis_bg.vbs into the Windows Startup folder
::  - starts JARVIS in the background right away (no window, no terminal)
::  - verifies that http://127.0.0.1:8000/health answers 200 OK
::  Run this ONCE. After that JARVIS starts with Windows by itself.
:: ===========================================================================

set "VBS=%~dp0start_jarvis_bg.vbs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%STARTUP%\JARVIS.lnk"
set "VENV_PY=%~dp0venv\Scripts\python.exe"
set "HEALTH=http://127.0.0.1:8000/health"

echo ============================================================
echo   JARVIS Forexcast Intelligence - silent auto-start setup
echo ============================================================
echo.

if not exist "%VENV_PY%" (
    echo [ERROR] venv Python nahi mila:
    echo         %VENV_PY%
    echo.
    echo Pehle ye chalayein:
    echo     python -m venv venv
    echo     venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist "%VBS%" (
    echo [ERROR] start_jarvis_bg.vbs nahi mila:
    echo         %VBS%
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0run_hidden.bat" (
    echo [ERROR] run_hidden.bat nahi mila:
    echo         %~dp0run_hidden.bat
    echo.
    pause
    exit /b 1
)

if not exist "%STARTUP%" mkdir "%STARTUP%"

echo [1/3] Windows Startup me shortcut bana raha hoon...
echo       %LNK%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $q=[char]34; $lnk=$ws.CreateShortcut('%LNK%'); $lnk.TargetPath='wscript.exe'; $lnk.Arguments=$q+'%VBS%'+$q; $lnk.WorkingDirectory='%~dp0'; $lnk.WindowStyle=7; $lnk.Description='JARVIS Forexcast Intelligence - silent background'; $lnk.Save()"

if not exist "%LNK%" (
    echo.
    echo [ERROR] Shortcut nahi ban saka.
    echo         Manually copy karein:
    echo             %VBS%
    echo         ko is folder me:
    echo             %STARTUP%
    echo.
    pause
    exit /b 1
)
echo       [OK] added to Startup.

echo.
echo [2/3] JARVIS background me start kar raha hoon...
start "" wscript.exe "%VBS%"

echo.
echo [3/3] Backend ka jawab check kar raha hoon: %HEALTH%
powershell -NoProfile -ExecutionPolicy Bypass -Command "for($i=0;$i -lt 45;$i++){ try{ $r=Invoke-WebRequest '%HEALTH%' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ Write-Host '       [OK] 200 OK - JARVIS backend online hai.'; exit 0 } }catch{}; Start-Sleep -Milliseconds 1000 }; Write-Host '       [FAIL] 45 second me bhi 200 OK nahi mila.'; exit 1"
if errorlevel 1 (
    echo.
    echo [WARN] Backend ne jawab nahi diya. Ye check karein:
    echo            %~dp0logs\backend.log
    echo            %~dp0logs\launcher.log
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   HO GAYA - JARVIS ab silent mode me chalta rahega.
echo.
echo   Backend   : http://127.0.0.1:8000   ^(200 OK verified^)
echo   Logs      : %~dp0logs\
echo   Tunnel URL: %~dp0logs\tunnel.log ke andar
echo               https://....trycloudflare.com
echo.
echo   Band karne ke liye : Task Manager me wscript.exe end karein
echo   Auto-start hatane ke liye : ye file delete karein
echo               %LNK%
echo ============================================================
echo.
pause
