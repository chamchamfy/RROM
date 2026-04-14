@echo off
mode con cols=120 lines=50
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion
set fastboot=bin\windows\all\fastboot.exe
if %PROCESSOR_ARCHITECTURE%==x86 (set cpuArch=x86) else set cpuArch=amd64

echo. ================= CONG CU FLASH ROM BY @chamchamfy ================
echo. 	Hom nay ngay: %DATE%
echo. 	Bay gio la: %TIME%
echo. 	Qua trinh Flash Rom se mat nhieu thoi gian
echo. 	Vui long cho cho den khi ket thuc!
echo. ===================================================================
echo.

if not exist %fastboot% echo. Khong tim thay: %fastboot% (Not found: %fastboot%). & pause & exit /B 1
echo. * Dang ket noi thiet bi...
echo. * Waiting for device...
echo.
set device=unknown
for /l %%i in (1,1,120) do (
    set /a tg=%%i*5
::    echo. "Thu ket noi lan %%i... (Da cho !tg! giay)"
    for /f "tokens=1" %%t in ('%fastboot% devices 2^>^&1 ^| findstr /v "List"') do (
        if "%%t" neq "" (
            for /f "usebackq tokens=2 delims=: " %%D in (`%fastboot% getvar product 2^>^&1 ^| findstr /b "product:"`) do set "device=%%D"
        )
    )
    if "!device!" neq "unknown" goto chay
    timeout /t 5 /nobreak >nul
)
echo. [ERROR]: Timeout: 10 mins
echo. [LOI]: Qua thoi gian cho 10 phut, khong tim thay thiet bi! 
echo. Nhan phim bat ki de thoat (Press any key to exit)...
pause >nul 2>nul
exit
:chay
set "hwc=" & for /f "tokens=3" %%A in ('%fastboot% oem hwid 2^>^&1 ^| findstr "\<HwCountry:"') do set hwc=%%A
set "b=boot" & %fastboot% getvar partition-size:init_boot 2>&1 | findstr /i "init_boot" >nul && set b=init_boot
set "thietbi=kb" & if "!device!" neq "!thietbi!" (echo. - Danh cho thiet bi [Compatible devices]: !thietbi! & echo. - Thiet bi cua ban [Your device]: !device! & pause & exit /B 1)
set "bl=no" & for /f "tokens=2 delims=: " %%U in ('%fastboot% getvar unlocked 2^>^&1 ^| findstr /l /c:"unlocked:"') do set bl=%%U
if /i "!bl!"=="no" (echo. [LOI]: Thiet bi chua Unlock Bootloader. [ERROR]: Bootloader is LOCKED. & pause & exit /B 1)
echo. * Thiet bi cua ban [Your device]: %device% - Khu vuc [Region]: %hwc%
echo.
if exist images\super.img.zst (
echo. - Dang chuyen doi phan vung super. Qua trinh nay co the mat vai phut tuy vao cau hinh may.
echo.   Converting super partition. This may take some time depending on your PC hardware.
echo. ! Luu y: O dia can trong toi thieu 10GB, neu khong qua trinh chuyen doi se that bai.
echo.   Note: At least 10GB of free disk space is required, otherwise the conversion will fail.
echo. - Bam phim bat ky de tiep tuc chuyen doi... 
echo.   Press any key to continue...
pause >nul 2>nul
bin\windows\%cpuArch%\zstd.exe --rm -d images\super.img.zst -o images\super.img
if "%errorlevel%" equ "0" (
    echo. - Chuyen doi thanh cong.
    echo.   Converted partition successfully.
    echo.
) else (
    echo. - Chuyen doi loi, nhan phim bat ky de thoat...
    echo.   Partition conversion failed, press any key to exit...
    pause >nul 2>nul
    exit
)
)

:Q1
echo. 1. Lan cai dat dau tien can xoa du lieu va bo nho trong cua ban. 
echo.    Flashing the first time will erase data and internal memory. 
set /p CHOICE1=" --> Ban co dong y khong? (Do you agree?) (Y/N): "
if /i "%CHOICE1%"=="y" goto Q2
if /i "%CHOICE1%"=="n" goto Q2
    goto Q1

:Q2
echo. 
if exist images\boot_magisk.img (
echo. * Cai dat boot_magisk.img (ROOT)?
echo.   Do you want to flash boot_magisk.img (ROOT)?
set /p CHOICE2=" --> Ban co dong y khong? (Do you agree?) (Y/N): "
) else (
    set CHOICE2=n
    goto MAIN
)
if /i "%CHOICE2%"=="y" goto MAIN
if /i "%CHOICE2%"=="n" goto MAIN
    goto Q2

:MAIN
echo. 2. Cap nhat firmware...
echo.    Flashing firmware...
if exist images\cmnlib64.mbn (
%fastboot% flash cmnlib64 images\cmnlib64.mbn
)
if exist images\xbl_config_5.elf (
%fastboot% flash xbl_config_5 images\xbl_config_5.elf
)
if exist images\NON-HLOS.bin (
%fastboot% flash modem images\NON-HLOS.bin
)
if exist images\cmnlib.mbn (
%fastboot% flash cmnlib images\cmnlib.mbn
)
if exist images\BTFM.bin (
%fastboot% flash bluetooth images\BTFM.bin
)
if exist images\km4.mbn (
%fastboot% flash keymaster images\km4.mbn
)
if exist images\xbl_5.elf (
%fastboot% flash xbl_5 images\xbl_5.elf
)
if exist images\tz.mbn (
%fastboot% flash tz images\tz.mbn
)
if exist images\aop.mbn (
%fastboot% flash aop images\aop.mbn
)
if exist images\featenabler.mbn (
%fastboot% flash featenabler images\featenabler.mbn
)
if exist images\xbl_config_4.elf (
%fastboot% flash xbl_config_4 images\xbl_config_4.elf
)
if exist images\storsec.mbn (
%fastboot% flash storsec images\storsec.mbn
)
if exist images\uefi_sec.mbn (
%fastboot% flash uefisecapp images\uefi_sec.mbn
)
if exist images\qupv3fw.elf (
%fastboot% flash qupfw images\qupv3fw.elf
)
if exist images\abl.elf (
%fastboot% flash abl images\abl.elf
)
if exist images\dspso.bin (
%fastboot% flash dsp images\dspso.bin
)
if exist images\devcfg.mbn (
%fastboot% flash devcfg images\devcfg.mbn
)
if exist images\xbl_4.elf (
%fastboot% flash xbl_4 images\xbl_4.elf
)
if exist images\hyp.mbn (
%fastboot% flash hyp images\hyp.mbn
)
if exist images\cmnlib64.mbn (
%fastboot% flash cmnlib64bak images\cmnlib64.mbn
)
if exist images\cmnlib.mbn (
%fastboot% flash cmnlibbak images\cmnlib.mbn
)
if exist images\tz.mbn (
%fastboot% flash tzbak images\tz.mbn
)
if exist images\aop.mbn (
%fastboot% flash aopbak images\aop.mbn
)
if exist images\storsec.mbn (
%fastboot% flash storsecbak images\storsec.mbn
)
if exist images\qupv3fw.elf (
%fastboot% flash qupfwbak images\qupv3fw.elf
)
if exist images\abl.elf (
%fastboot% flash ablbak images\abl.elf
)
if exist images\devcfg.mbn (
%fastboot% flash devcfgbak images\devcfg.mbn
)
if exist images\hyp.mbn (
%fastboot% flash hypbak images\hyp.mbn
)
if exist images\logo.img (
%fastboot% flash logo images\logo.img
)
if exist images\dtbo.img (
%fastboot% flash dtbo images\dtbo.img
)
if exist images\vbmeta.img (
%fastboot% flash vbmeta images\vbmeta.img
)
if exist images\vbmeta_system.img (
%fastboot% flash vbmeta_system images\vbmeta_system.img
)
if "%CHOICE2%" == "y" (
    %fastboot% flash boot images\boot_magisk.img
) else if "%CHOICE2%" == "n" (
    %fastboot% flash boot images\boot.img
)
if exist images\cust.img (
%fastboot% flash cust images\cust.img
)
if exist images\cust.img.0 (
%fastboot% flash cust images\cust.img.0
%fastboot% flash cust images\cust.img.1
)
::if exist images\persist.img (
::%fastboot% flash persist images\persist.img
::%fastboot% flash persistbak images\persistbak.img
::)
if exist images\splash.img (
%fastboot% flash splash images\splash.img
)
if exist images\recovery.img (
%fastboot% flash recovery images\recovery.img
)
if exist images\super.img (
echo. 3. Cap nhat phan vung super... (Tep tin nay rat lon, vui long cho!)
echo.    Flashing the super partition... (This file is very large, please wait!)
%fastboot% flash super images\super.img
)
if "%CHOICE1%" == "y" (
    %fastboot% erase userdata
    %fastboot% erase metadata
)
%fastboot% reboot
echo.
pause