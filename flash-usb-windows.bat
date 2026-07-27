@echo off
REM AI Rescue USB - Windows Flash Tool
REM ===================================
REM Flash the AI Rescue USB image to a USB drive on Windows

setlocal enabledelayedexpansion

echo.
echo ========================================
echo    AI Rescue USB - Windows Flash Tool
echo ========================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This tool requires administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if USB image exists
set "IMAGE_FILE=build\ai-rescue-usb.img"
if not exist "%IMAGE_FILE%" (
    echo [ERROR] USB image not found: %IMAGE_FILE%
    echo Please run build-all.sh first to create the image.
    pause
    exit /b 1
)

echo Found USB image: %IMAGE_FILE%
echo.

REM List available USB drives
echo Available USB drives:
echo.

wmic diskdrive where "InterfaceType='USB'" get DeviceID,Model,Size /format:list | findstr /i "DeviceID Model Size" > %TEMP%\usb_list.txt

set counter=0
for /f "tokens=2 delims==" %%a in ('type %TEMP%\usb_list.txt ^| findstr /i "DeviceID"') do (
    set /a counter+=1
    set "device[!counter!]=%%a"
)

for /f "tokens=2 delims==" %%a in ('type %TEMP%\usb_list.txt ^| findstr /i "Model"') do (
    set /a counter+=1
    set "model[!counter!]=%%a"
)

for /f "tokens=2 delims==" %%a in ('type %TEMP%\usb_list.txt ^| findstr /i "Size"') do (
    set /a counter+=1
    set "size[!counter!]=%%a"
)

if !counter! equ 0 (
    echo [ERROR] No USB drives detected.
    echo Please insert a USB drive and try again.
    pause
    exit /b 1
)

REM Display USB drives
for /l %%i in (1,1,%counter%) do (
    echo %%i. !device[%%i]! - !model[%%i]! - !size[%%i]! bytes
)
echo.

REM Ask user to select USB drive
set /p "selection=Select USB drive number (1-%counter%): "

if not defined selection (
    echo [ERROR] No selection made.
    pause
    exit /b 1
)

REM Validate selection
set /a max_sel=%counter%
if %selection% lss 1 goto :invalid_selection
if %selection% gtr %max_sel% goto :invalid_selection

set "selected_device=!device[%selection%]!"
set "selected_model=!model[%selection%]!"

echo.
echo ========================================
echo WARNING: This will erase ALL data on:
echo   Device: %selected_device%
echo   Model: %selected_model%
echo ========================================
echo.

set /p "confirm=Type 'YES' to confirm: "
if /i not "%confirm%"=="YES" (
    echo Operation cancelled.
    pause
    exit /b 0
)

echo.
echo Flashing USB image...
echo This may take several minutes.
echo.

REM Use dd for Windows (if available) or PowerShell
where dd >nul 2>&1
if %errorlevel% equ 0 (
    echo Using dd to flash...
    dd if="%IMAGE_FILE%" of=%selected_device% bs=4M status=progress
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] USB drive flashed successfully!
        echo You can now boot from this USB drive.
    ) else (
        echo.
        echo [ERROR] Failed to flash USB drive.
    )
) else (
    echo Fallback: Using PowerShell (dd not found)...
    echo.
    echo PowerShell method requires manual intervention.
    echo Please use Rufus or Etcher to flash: %IMAGE_FILE%
    echo.
    echo Recommended tools:
    echo   - Rufus: https://rufus.akeo.ie/
    echo   - BalenaEtcher: https://www.balena.io/etcher/
    echo   - Win32DiskImager: https://sourceforge.net/projects/win32diskimager/
)

echo.
pause
exit /b 0

:invalid_selection
echo [ERROR] Invalid selection.
pause
exit /b 1
