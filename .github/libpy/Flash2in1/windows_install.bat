@echo off
mode con cols=100 lines=30
set fastboot=bin\windows\all\fastboot.exe
if %PROCESSOR_ARCHITECTURE%==x86 (set cpuArch=x86) else set cpuArch=amd64

echo. ==== FLASH ROM BY @chamchamfy ====
echo. |DATE
echo.
echo.
if exist images\super.img.zst (
eecho. Bat dau chuyen doi phan vung super. Co the mat nhieu thoi gian, tuy thuoc vao cau hinh may tinh cua ban.
echo. Start converting super partition. It may take a long time, depending on your computer configuration.
echo. Luu y: Dung luong trong cua phan vung hien tai cua ban phai lon hon 10GB, neu khong qua trinh chuyen doi super se khong thanh cong. 
echo. Note: Please ensure that the free size of the current partition is greater than 10GB, otherwise the super conversion will fail.
echo. Bam phim bat ky de tiep tuc chuyen doi... 
echo. Press any key to continue...
pause >nul 2>nul
bin\windows\%cpuArch%\zstd.exe --rm -d images\super.img.zst -o images\super.img
if %errorlevel% == 1 (
    echo. Chuyen doi khong thanh cong, nhan phim bat ky de thoat.
	echo. Conversion process error, press any key to exit...
    pause >nul 2>nul
    exit
)
echo. Chuyen doi thanh cong.
echo. Converted super partition successfully.
echo.
)


:Q1
echo. 1. Lan cai dat dau tien yeu cau xoa du lieu va bo nho trong cua ban. 
echo. 1. Flashing the first time will erase data and internal memory. 
set /p CHOICE1=" --> Ban co dong y khong? (Do you agree?) (Y/N): "
if /i "%CHOICE1%" == "y" (
    goto Q2
) else if /i "%CHOICE1%" == "n" (
    goto Q2
) else (
    goto Q1
)

:Q2
echo. 
echo. 2. Cai dat boot_magisk.img (ROOT)?
echo. 2. Do you want to flash boot_magisk.img (ROOT)?
set /p CHOICE2=" --> Ban co dong y khong? (Do you agree?) (Y/N): "
if /i "%CHOICE2%" == "y" (
    goto MAIN
) else if /i "%CHOICE2%" == "n" (
    goto MAIN
) else (
    goto Q2
)
goto MAIN

:MAIN
if exist images\cmnlib64.mbn (
%fastboot% %* flash cmnlib64 images\cmnlib64.mbn
)
if exist images\xbl_config_5.elf (
%fastboot% %* flash xbl_config_5 images\xbl_config_5.elf
)
if exist images\NON-HLOS.bin (
%fastboot% %* flash modem images\NON-HLOS.bin
)
if exist images\cmnlib.mbn (
%fastboot% %* flash cmnlib images\cmnlib.mbn
)
if exist images\BTFM.bin (
%fastboot% %* flash bluetooth images\BTFM.bin
)
if exist images\km4.mbn (
%fastboot% %* flash keymaster images\km4.mbn
)
if exist images\xbl_5.elf (
%fastboot% %* flash xbl_5 images\xbl_5.elf
)
if exist images\tz.mbn (
%fastboot% %* flash tz images\tz.mbn
)
if exist images\aop.mbn (
%fastboot% %* flash aop images\aop.mbn
)
if exist images\featenabler.mbn (
%fastboot% %* flash featenabler images\featenabler.mbn
)
if exist images\xbl_config_4.elf (
%fastboot% %* flash xbl_config_4 images\xbl_config_4.elf
)
if exist images\storsec.mbn (
%fastboot% %* flash storsec images\storsec.mbn
)
if exist images\uefi_sec.mbn (
%fastboot% %* flash uefisecapp images\uefi_sec.mbn
)
if exist images\qupv3fw.elf (
%fastboot% %* flash qupfw images\qupv3fw.elf
)
if exist images\abl.elf (
%fastboot% %* flash abl images\abl.elf
)
if exist images\dspso.bin (
%fastboot% %* flash dsp images\dspso.bin
)
if exist images\devcfg.mbn (
%fastboot% %* flash devcfg images\devcfg.mbn
)
if exist images\xbl_4.elf (
%fastboot% %* flash xbl_4 images\xbl_4.elf
)
if exist images\hyp.mbn (
%fastboot% %* flash hyp images\hyp.mbn
)
if exist images\cmnlib64.mbn (
%fastboot% %* flash cmnlib64bak images\cmnlib64.mbn
)
if exist images\cmnlib.mbn (
%fastboot% %* flash cmnlibbak images\cmnlib.mbn
)
if exist images\tz.mbn (
%fastboot% %* flash tzbak images\tz.mbn
)
if exist images\aop.mbn (
%fastboot% %* flash aopbak images\aop.mbn
)
if exist images\storsec.mbn (
%fastboot% %* flash storsecbak images\storsec.mbn
)
if exist images\qupv3fw.elf (
%fastboot% %* flash qupfwbak images\qupv3fw.elf
)
if exist images\abl.elf (
%fastboot% %* flash ablbak images\abl.elf
)
if exist images\devcfg.mbn (
%fastboot% %* flash devcfgbak images\devcfg.mbn
)
if exist images\hyp.mbn (
%fastboot% %* flash hypbak images\hyp.mbn
)
if exist images\logo.img (
%fastboot% %* flash logo images\logo.img
)
if exist images\dtbo.img (
%fastboot% %* flash dtbo images\dtbo.img
)
if exist images\vbmeta.img (
%fastboot% %* flash vbmeta images\vbmeta.img
)
if exist images\vbmeta_system.img (
%fastboot% %* flash vbmeta_system images\vbmeta_system.img
)
@REM flash firmware done

if /i "%CHOICE2%" == "y" (
    %fastboot% %* flash boot images\boot_magisk.img
) else if /i "%CHOICE2%" == "n" (
    %fastboot% %* flash boot images\boot.img
)
if exist images\super.img (
echo. Bat dau flash super. Tep nay lon va co the mat nhieu thoi gian, tuy thuoc vao cau hinh may tinh cua ban. 
echo. Start flashing super. This file is large and may take a long time depending on your computer configuration.
%fastboot% %* flash super images\super.img
)
%fastboot% %* flash cust images\cust.img
if exist images\recovery.img (
%fastboot% %* flash recovery images\recovery.img
)
if /i "%CHOICE1%" == "y" (
    %fastboot% %* erase userdata
    %fastboot% %* erase metadata
)
%fastboot% %* reboot
echo.
echo.
:Finish
goto Finish
:END