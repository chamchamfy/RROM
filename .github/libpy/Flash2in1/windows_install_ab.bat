@echo off
mode con cols=100 lines=30
set fastboot=bin\windows\all\fastboot.exe
if %PROCESSOR_ARCHITECTURE%==x86 (set cpuArch=x86) else set cpuArch=amd64

echo. ==== FLASH ROM BY @chamchamfy ====
echo. |DATE
echo.
echo.
if exist images\super.img.zst (
echo. Bat dau chuyen doi phan vung super. Co the mat nhieu thoi gian, tuy thuoc vao cau hinh may tinh cua ban.
echo. Start converting super partition. It may take a long time, depending on your computer configuration.
echo. Luu y: Dung luong trong cua phan vung hien tai cua ban phai lon hon 10GB, neu khong qua trinh chuyen doi super se khong thanh cong. 
echo. Note: Please ensure that the free size of the current partition is greater than 10GB, otherwise the super conversion will fail.
echo. Bam phim bat ky de tiep tuc chuyen doi... 
echo. Press any key to continue...
pause >nul 2>nul
bin\windows\%cpuArch%\zstd.exe --rm -d images\super.img.zst -o images\super.img
if %errorlevel% == 1 (
    echo. Chuyen doi khong thanh cong, nhan phim bat ky de thoat...
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
if exist images\abl.img (
%fastboot% %* flash abl_ab images\abl.img
)
if exist images\aop.img (
%fastboot% %* flash aop_ab images\aop.img
)
if exist images\bluetooth.img (
%fastboot% %* flash bluetooth_ab images\bluetooth.img
)
if exist images\cmnlib64.img (
%fastboot% %* flash cmnlib64_ab images\cmnlib64.img
)
if exist images\cmnlib.img (
%fastboot% %* flash cmnlib_ab images\cmnlib.img
)
if exist images\cpucp.img (
%fastboot% %* flash cpucp_ab images\cpucp.img
)
if exist images\devcfg.img (
%fastboot% %* flash devcfg_ab images\devcfg.img
)
if exist images\dsp.img (
%fastboot% %* flash dsp_ab images\dsp.img
)
if exist images\dtbo.img (
%fastboot% %* flash dtbo_ab images\dtbo.img
)
if exist images\featenabler.img (
%fastboot% %* flash featenabler_ab images\featenabler.img
)
if exist images\hyp.img (
%fastboot% %* flash hyp_ab images\hyp.img
)
if exist images\imagefv.img (
%fastboot% %* flash imagefv_ab images\imagefv.img
)
if exist images\keymaster.img (
%fastboot% %* flash keymaster_ab images\keymaster.img
)
if exist images\modem.img (
%fastboot% %* flash modem_ab images\modem.img
)
if exist images\qupfw.img (
%fastboot% %* flash qupfw_ab images\qupfw.img
)
if exist images\shrm.img (
%fastboot% %* flash shrm_ab images\shrm.img
)
if exist images\tz.img (
%fastboot% %* flash tz_ab images\tz.img
)
if exist images\uefisecapp.img (
%fastboot% %* flash uefisecapp_ab images\uefisecapp.img
)
if exist images\vbmeta.img (
%fastboot% %* flash vbmeta_ab images\vbmeta.img
)
if exist images\vbmeta_system.img (
%fastboot% %* flash vbmeta_system_ab images\vbmeta_system.img
)
if exist images\vendor_boot.img (
%fastboot% %* flash vendor_boot_ab images\vendor_boot.img
)
if exist images\xbl_config.img (
%fastboot% %* flash xbl_config_ab images\xbl_config.img
)
if exist images\xbl.img (
%fastboot% %* flash xbl_ab images\xbl.img
)
@REM flash firmware done

if /i "%CHOICE2%" == "y" (
    %fastboot% %* flash boot_ab images\boot_magisk.img
) else if /i "%CHOICE2%" == "n" (
    %fastboot% %* flash boot_ab images\boot.img
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
%fastboot% %* set_active a
%fastboot% %* reboot
echo.
echo.
:Finish
goto Finish
:END