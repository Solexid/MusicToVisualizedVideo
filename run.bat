@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   Music To Visualized Video - Launcher
echo ============================================
echo.

:: Check Python installation
echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python not found!
    echo.
    echo Opening Python download page...
    start https://www.python.org/downloads/
    echo.
    echo Please install Python 3.8 or higher,
    echo then run this file again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo       Found version: !PYTHON_VERSION!
echo.

:: Check and install requirements
echo [2/4] Checking dependencies...
if not exist "requirements.txt" (
    echo [WARN] requirements.txt not found, skipping
    echo.
) else (
    echo       Checking installed packages...
    python -c "import pkg_resources; pkg_resources.working_set.require(open('requirements.txt').read().splitlines())" >nul 2>&1
    if %errorlevel% neq 0 (
        echo       Installing dependencies...
        echo.
        python -m pip install --upgrade pip --quiet
        python -m pip install -r requirements.txt --quiet
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] Failed to install dependencies!
            echo.
            pause
            exit /b 1
        )
        echo       Done!
    ) else (
        echo       All dependencies installed
    )
    echo.
)

:: Check FFmpeg
echo [3/4] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    echo       FFmpeg found in PATH
    echo.
) else (
    if exist "ffmpeg.exe" (
        echo       FFmpeg found in local folder
        echo.
    ) else (
        echo       FFmpeg not found. Downloading...
        echo.
        
        :: Download FFmpeg
        set FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
        set FFMPEG_ZIP=%TEMP%\ffmpeg.zip
        
        echo       Downloading FFmpeg...
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!FFMPEG_URL!' -OutFile '!FFMPEG_ZIP!'}"
        
        if exist "!FFMPEG_ZIP!" (
            echo       Extracting...
            powershell -Command "& {Expand-Archive -Path '!FFMPEG_ZIP!' -DestinationPath '%TEMP%\ffmpeg_extract' -Force}"
            
            :: Find ffmpeg.exe in extracted folder
            for /d %%d in ("%TEMP%\ffmpeg_extract\ffmpeg-*") do set FFMPEG_EXTRACT_DIR=%%d
            
            if exist "!FFMPEG_EXTRACT_DIR!\bin\ffmpeg.exe" (
                copy "!FFMPEG_EXTRACT_DIR!\bin\ffmpeg.exe" "." >nul
                echo       FFmpeg downloaded successfully!
            ) else (
                echo [WARN] Could not find ffmpeg.exe in archive
            )
            
            :: Cleanup
            del "!FFMPEG_ZIP!" 2>nul
            rmdir /s /q "%TEMP%\ffmpeg_extract" 2>nul
        ) else (
            echo [WARN] Failed to download FFmpeg
            echo.
            echo Download manually from:
            echo https://www.gyan.dev/ffmpeg/builds/
            echo.
        )
        echo.
    )
)

:: Run GUI
echo [4/4] Starting GUI...
echo.
echo ============================================
echo Starting Music To Visualized Video GUI
echo ============================================
echo.

python gui.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start GUI!
    echo.
    pause
    exit /b %errorlevel%
)

endlocal
