@echo off
mode con cols=140 lines=50
set fastboot=bin\windows\all\fastboot.exe
if %PROCESSOR_ARCHITECTURE%==x86 (set cpuArch=x86) else set cpuArch=amd64

echo. ==== FLASH ROM BY @chamchamfy ====
echo. %DATE%
echo. %TIME%
echo.
echo.
if not exist %fastboot% echo %fastboot% not found. & pause & exit /B 1
echo. * Dang ket noi thiet bi...
echo. * Waiting for device...
set device=unknown
set thietbi=kb
for /f "tokens=2" %%D in ('%fastboot% getvar product 2^>^&1 ^| findstr /l /b /c:"product:"') do set device=%%D
if "%device%" neq "%thietbi%" echo. - Danh cho thiet bi (Compatible devices): %thietbi% & echo. - Thiet bi cua ban (Your device): %device% & pause & exit /B 1
echo. * Thiet bi cua ban (Your device): %device%
echo.
if exist images\super.img.zst (
echo. - Dang chuyen doi phan vung super. Co the mat nhieu thoi gian, tuy thuoc vao cau hinh may tinh cua ban.
echo.   Converting super partition. It may take a long time, depending on your computer configuration.
echo. ! Luu y: Dung luong trong o dia hien tai cua ban phai lon hon 10GB, neu khong qua trinh chuyen doi super se khong thanh cong. 
echo.   Note: Make sure the free space in your current drive is greater than 10GB, otherwise the super partition conversion process will fail.
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
if "%CHOICE1%" == "y" (
    goto Q2
) else if "%CHOICE1%" == "n" (
    goto Q2
) else (
    goto Q1
)

:Q2
echo. 
if exist images\boot_magisk.img (
echo. * Cai dat boot_magisk.img (ROOT)?
echo.   Do you want to flash boot_magisk.img (ROOT)?
set /p CHOICE2=" --> Ban co dong y khong? (Do you agree?) (Y/N): "
if "%CHOICE2%" == "y" (
    goto MAIN
) else if "%CHOICE2%" == "n" (
    goto MAIN
) else (
    goto Q2
)
) else (
    set CHOICE2=n
    goto MAIN
)

:MAIN
echo. 2. Cap nhat firmware...
echo.    Flashing firmware...
if exist images\abl.img (
%fastboot% flash abl_ab images\abl.img
)
if exist images\aop.img (
%fastboot% flash aop_ab images\aop.img
)
if exist images\aop_config.img (
%fastboot% flash aop_config_ab images\aop_config.img
)
if exist images\bluetooth.img (
%fastboot% flash bluetooth_ab images\bluetooth.img
)
if exist images\cmnlib64.img (
%fastboot% flash cmnlib64_ab images\cmnlib64.img
)
if exist images\cmnlib.img (
%fastboot% flash cmnlib_ab images\cmnlib.img
)
if exist images\countrycode.img (
%fastboot% flash countrycode_ab images\countrycode.img
)
if exist images\cpucp.img (
%fastboot% flash cpucp_ab images\cpucp.img
)
if exist images\cpucp_dtb.img (
%fastboot% flash cpucp_dtb_ab images\cpucp_dtb.img
)
if exist images\devcfg.img (
%fastboot% flash devcfg_ab images\devcfg.img
)
if exist images\dsp.img (
%fastboot% flash dsp_ab images\dsp.img
)
if exist images\dtbo.img (
%fastboot% flash dtbo_ab images\dtbo.img
)
if exist images\featenabler.img (
%fastboot% flash featenabler_ab images\featenabler.img
)
if exist images\hyp.img (
%fastboot% flash hyp_ab images\hyp.img
)
if exist images\imagefv.img (
%fastboot% flash imagefv_ab images\imagefv.img
)
if exist images\init_boot.img (
%fastboot% flash init_boot_ab images\init_boot.img
)
if exist images\keymaster.img (
%fastboot% flash keymaster_ab images\keymaster.img
)
if exist images\modem.img (
%fastboot% flash modem_ab images\modem.img
)
if exist images\modemfirmware.img (
%fastboot% flash modemfirmware_ab images\modemfirmware.img
)
if exist images\multiimgqti.img (
%fastboot% flash multiimgqti_ab images\multiimgqti.img
)
if exist images\qupfw.img (
%fastboot% flash qupfw_ab images\qupfw.img
)
if exist images\shrm.img (
%fastboot% flash shrm_ab images\shrm.img
)
if exist images\spuservice.img (
%fastboot% flash spuservice_ab images\spuservice.img
)
if exist images\tz.img (
%fastboot% flash tz_ab images\tz.img
)
if exist images\uefi.img (
%fastboot% flash uefi_ab images\uefi.img
)
if exist images\uefisecapp.img (
%fastboot% flash uefisecapp_ab images\uefisecapp.img
)
if exist images\vbmeta.img (
%fastboot% flash vbmeta_ab images\vbmeta.img
)
if exist images\vbmeta_system.img (
%fastboot% flash vbmeta_system_ab images\vbmeta_system.img
)
if exist images\vbmeta_vendor.img (
%fastboot% flash vbmeta_vendor_ab images\vbmeta_vendor.img
)
if exist images\vendor_boot.img (
%fastboot% flash vendor_boot_ab images\vendor_boot.img
)
if exist images\vm-bootsys.img (
%fastboot% flash vm-bootsys_ab images\vm-bootsys.img
)
if exist images\xbl_ramdump.img (
%fastboot% flash xbl_ramdump_ab images\xbl_ramdump.img
)
if exist images\xbl_config.img (
%fastboot% flash xbl_config_ab images\xbl_config.img
)
if exist images\xbl.img (
%fastboot% flash xbl_ab images\xbl.img
)

if "%CHOICE2%" == "y" (
    %fastboot% flash boot_ab images\boot_magisk.img
) else if "%CHOICE2%" == "n" (
    %fastboot% flash boot_ab images\boot.img
)
if exist images\super.img (
echo. 3. Cap nhat phan vung super. Tep nay lon va co the mat nhieu thoi gian, tuy thuoc vao cau hinh may tinh cua ban.
echo.    Flashing super partition. This file is large and may take a long time depending on your computer configuration.
%fastboot% flash super images\super.img
)
if exist images\cust.img (
%fastboot% flash cust images\cust.img
)
if exist images\cust.img.0 (
%fastboot% flash cust images\cust.img.0
%fastboot% flash cust images\cust.img.1
)
)
if exist images\persist.img (
%fastboot% flash persist images\persist.img
%fastboot% flash persistbak images\persistbak.img
)
if exist images\splash.img (
%fastboot% flash splash images\splash.img
)
if exist images\recovery.img (
%fastboot% flash recovery_ab images\recovery.img
)
if "%CHOICE1%" == "y" (
    %fastboot% erase userdata
    %fastboot% erase metadata
)
%fastboot% set_active a
%fastboot% reboot
echo.
pause