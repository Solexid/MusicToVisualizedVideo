@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   Music To Visualized Video - Build Script
echo ============================================
echo.

:: Get current date for release folder (works on any Windows locale)
for /f "delims=" %%i in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set DATETIME=%%i
set RELEASE_DIR=release_%DATETIME%

echo [1/5] Creating release directory...
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
echo       Created: %RELEASE_DIR%
echo.

:: Check Python
echo [2/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo       Python: !PYTHON_VERSION!
echo.

:: Install PyInstaller if needed
echo [3/5] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing PyInstaller...
    pip install pyinstaller --quiet
) else (
    echo       PyInstaller already installed
)
echo.

:: Build with PyInstaller
echo [4/5] Building executable...
echo       This may take a few minutes...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "MusicToVisualizedVideo" ^
    --icon=NONE ^
    --add-data "viz_filters.py;." ^
    --add-data "core.py;." ^
    --add-data "gui.py;." ^
    --add-data "circle.glsl;." ^
    --add-data "polar.glsl;." ^
    --hidden-import pkg_resources ^
    --hidden-import mutagen ^
    --hidden-import PIL ^
    --hidden-import chardet ^
    --hidden-import tqdm ^
    --clean ^
    gui.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo       Build successful!
echo.

:: Copy files to release directory
echo [5/5] Preparing release package...

:: Copy executable
if exist "dist\MusicToVisualizedVideo.exe" (
    copy /Y "dist\MusicToVisualizedVideo.exe" "%RELEASE_DIR%" >nul 2>&1
    echo       Copied: MusicToVisualizedVideo.exe
) else (
    echo [ERROR] Executable not found!
    pause
    exit /b 1
)

:: Copy ffmpeg if exists
if exist "ffmpeg.exe" (
    copy /Y "ffmpeg.exe" "%RELEASE_DIR%" >nul 2>&1
    echo       Copied: ffmpeg.exe
) else (
    echo [INFO] ffmpeg.exe not found in current folder
    echo       Downloading FFmpeg...
    
    set FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    set FFMPEG_ZIP=%TEMP%\ffmpeg.zip
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!FFMPEG_URL!' -OutFile '!FFMPEG_ZIP!'}"
    
    if exist "!FFMPEG_ZIP!" (
        powershell -Command "& {Expand-Archive -Path '!FFMPEG_ZIP!' -DestinationPath '%TEMP%\ffmpeg_build' -Force}"
        for /d %%d in ("%TEMP%\ffmpeg_build\ffmpeg-*") do set FFMPEG_EXTRACT_DIR=%%d
        if exist "!FFMPEG_EXTRACT_DIR!\bin\ffmpeg.exe" (
            copy /Y "!FFMPEG_EXTRACT_DIR!\bin\ffmpeg.exe" "%RELEASE_DIR%" >nul 2>&1
            echo       Downloaded: ffmpeg.exe
        )
        del "!FFMPEG_ZIP!" 2>nul
        rmdir /s /q "%TEMP%\ffmpeg_build" 2>nul
    )
)

:: Copy requirements
if exist "requirements.txt" (
    copy /Y "requirements.txt" "%RELEASE_DIR%" >nul 2>&1
    echo       Copied: requirements.txt
)

:: Copy README
if exist "README.md" (
    copy /Y "README.md" "%RELEASE_DIR%" >nul 2>&1
    echo       Copied: README.md
)

:: Copy LICENSE
if exist "LICENSE" (
    copy /Y "LICENSE" "%RELEASE_DIR%" >nul 2>&1
    echo       Copied: LICENSE
)

:: Create run.bat for release
(
echo @echo off
echo echo Starting Music To Visualized Video...
echo MusicToVisualizedVideo.exe
echo if %%errorlevel%% neq 0 ^(
echo     echo Failed to start!
echo     pause
echo ^)
) > "%RELEASE_DIR%\run.bat"
echo       Created: run.bat

echo.
echo       Creating ZIP archive...
powershell -Command "& {Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath 'MusicToVisualizedVideo_%DATETIME%.zip' -Force}"

if exist "MusicToVisualizedVideo_%DATETIME%.zip" (
    echo       Created: MusicToVisualizedVideo_%DATETIME%.zip
) else (
    echo [WARN] Failed to create ZIP archive
)

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Release folder: %RELEASE_DIR%
echo Archive: MusicToVisualizedVideo_%DATETIME%.zip
echo.

:: Cleanup build artifacts
echo Cleaning up build artifacts...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del "MusicToVisualizedVideo.spec" 2>nul
echo       Done!
echo.

endlocal
