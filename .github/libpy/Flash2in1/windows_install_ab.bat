@echo off
mode con cols=120 lines=50
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion
set fastboot=bin\windows\all\fastboot.exe
if %PROCESSOR_ARCHITECTURE%==x86 (set cpuArch=x86) else set cpuArch=amd64

echo. ================= CÔNG CỤ FLASH ROM BY @chamchamfy ================
echo. 	Hôm nay ngày: %DATE%
echo. 	Bây giờ là: %TIME%
echo. 	Quá trình Flash Rom sẽ mất nhiều thời gian
echo. 	Vui lòng chờ cho đến khi kết thúc!
echo. ===================================================================
echo.

if not exist %fastboot% echo. Không tìm thấy: %fastboot% (Not found: %fastboot%). & pause & exit /B 1
echo. * Đang kết nối thiết bị...
echo. * Waiting for device...
echo.
set device=unknown
for /l %%i in (1,1,120) do (
    set /a tg=%%i*5
::    echo. "Thử kết nối lần %%i... (Đã chờ !tg! giây)"
    for /f "tokens=1" %%t in ('%fastboot% devices 2^>^&1 ^| findstr /v "List"') do (
        if "%%t" neq "" (
            for /f "usebackq tokens=2 delims=: " %%D in (`%fastboot% getvar product 2^>^&1 ^| findstr /b "product:"`) do set "device=%%D"
        )
    )
    if "!device!" neq "unknown" goto chay
    timeout /t 5 /nobreak >nul
)
echo. [ERROR]: Timeout: 10 mins
echo. [LỖI]: Quá thời gian chờ 10 phút, không tìm thấy thiết bị! 
echo. Nhấn phím bất kì để thoát (Press any key to exit)...
pause >nul 2>nul
exit
:chay
set "hwc=" & for /f "tokens=3" %%A in ('%fastboot% oem hwid 2^>^&1 ^| findstr "\<HwCountry:"') do set hwc=%%A
set "b=boot" & %fastboot% getvar partition-size:init_boot 2>&1 | findstr /i "init_boot" >nul && set b=init_boot
set "thietbi=kb" & if "!device!" neq "!thietbi!" (echo. - Dành cho thiết bị [Compatible devices]: !thietbi! & echo. - Thiết bị của bạn [Your device]: !device! & pause & exit /B 1)
set "bl=no" & for /f "tokens=2 delims=: " %%U in ('%fastboot% getvar unlocked 2^>^&1 ^| findstr /l /c:"unlocked:"') do set bl=%%U
if /i "!bl!"=="no" (echo. [LỖI]: Thiết bị chưa Unlock Bootloader. [ERROR]: Bootloader is LOCKED. & pause & exit /B 1)
echo. * Thiết bị của bạn [Your device]: %device% - Khu vực [Region]: %hwc%
echo.

if exist images\super.img.zst (
echo. - Đang chuyển đổi phân vùng super. Quá trình này có thể mất vài phút tùy vào cấu hình máy.
echo.   Converting super partition. This may take some time depending on your PC hardware.
echo. ! Lưu ý: Ổ đĩa cần trống tối thiểu 10GB, nếu không quá trình chuyển đổi sẽ thất bại.
echo.   Note: At least 10GB of free disk space is required, otherwise the conversion will fail.
echo. - Bấm phím bất kỳ để tiếp tục chuyển đổi... 
echo.   Press any key to continue...
pause >nul 2>nul
bin\windows\%cpuArch%\zstd.exe --rm -d images\super.img.zst -o images\super.img
if "%errorlevel%" equ "0" (
    echo. - Chuyển đổi thành công.
    echo.   Converted partition successfully.
    echo.
) else (
    echo. - Chuyển đổi thất bại, ấn phím bất kì để thoát...
    echo.   Partition conversion failed, press any key to exit...
    pause >nul 2>nul
    exit
)
)

:Q1
echo. 1. Lần cài đặt đầu tiên sẽ xoá dữ liệu và bộ nhớ máy của bạn. 
echo.    Flashing the first time will erase data and internal memory. 
set CHON1=
set /p CHON1=" --> Bạn có đồng ý không? (Do you agree?) (Y/N): "
if /i "%CHON1%"=="y" goto Q2
if /i "%CHON1%"=="n" goto Q2
echo. [!] Lựa chọn không hợp lệ
    goto Q1

:Q2
echo.
set CHON2=
set R=0
if exist images\boot_magisk.img set R=1
if exist images\boot_ksu.img set R=1
if exist images\init_boot_magisk.img set R=1
if exist images\init_boot_ksu.img set R=1
if "%R%"=="1" (
echo. * Cài đặt ROOT (magisk/KSU)?
echo.   Flash ROOT (magisk/KSU)?
set /p CHON2=" --> Lựa chọn (Input select) (M:Magisk /K:KernelSu /N: Không): "
) else (
    set CHON2=n
    goto MAIN
)
if /i "%CHON2%"=="m" goto MAIN
if /i "%CHON2%"=="k" goto MAIN
if /i "%CHON2%"=="n" goto MAIN
echo. [!] Lựa chọn không hợp lệ
    goto Q2

:MAIN
echo. 2. Cập nhật firmware...
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
if exist images\dcp.img (
%fastboot% flash dcp_ab images\dcp.img
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
if exist images\hyp_ac_config.img (
%fastboot% flash hyp_ac_config_ab images\hyp_ac_config.img
)
if exist images\idmanager.img (
%fastboot% flash idmanager_ab images\idmanager.img
)
if exist images\imagefv.img (
%fastboot% flash imagefv_ab images\imagefv.img
)
if exist images\keymaster.img (
%fastboot% flash keymaster_ab images\keymaster.img
)
if exist images\modem.img (
%fastboot% flash modem_ab images\modem.img
)
if "%hwc%"=="CN" if exist images\modemfirmware.img (
%fastboot% flash modemfirmware_ab images\modemfirmware.img
)
if not "%hwc%"=="CN" if exist images\modemfirmware_ww.img (
%fastboot% flash modemfirmware_ab images\modemfirmware_ww.img
)
if exist images\multiimgqti.img (
%fastboot% flash multiimgqti_ab images\multiimgqti.img
)
if exist images\pdp.img (
%fastboot% flash pdp_ab images\pdp.img
)
if exist images\pdp_cdb.img (
%fastboot% flash pdp_cdb_ab images\pdp_cdb.img
)
if exist images\pvmfw.img (
%fastboot% flash pvmfw_ab images\pvmfw.img
)
if exist images\qtvm_dtbo.img (
%fastboot% flash qtvm_dtbo_ab images\qtvm_dtbo.img
)
if exist images\qupfw.img (
%fastboot% flash qupfw_ab images\qupfw.img
)
if exist images\secretkeeper.img (
%fastboot% flash secretkeeper_ab images\secretkeeper.img
)
if exist images\shrm.img (
%fastboot% flash shrm_ab images\shrm.img
)
if exist images\soccp.img (
%fastboot% flash soccp_ab images\soccp.img
)
if exist images\soccp_dcd.img (
%fastboot% flash soccp_dcd_ab images\soccp_dcd.img
)
if exist images\soccp_debug.img (
%fastboot% flash soccp_debug_ab images\soccp_debug.img
)
if exist images\spuservice.img (
%fastboot% flash spuservice_ab images\spuservice.img
)
if exist images\tme_config.img (
%fastboot% flash tme_config_ab images\tme_config.img
)
if exist images\tme_fw.img (
%fastboot% flash tme_fw_ab images\tme_fw.img
)
if exist images\tme_seq_patch.img (
%fastboot% flash tme_seq_patch_ab images\tme_seq_patch.img
)
if exist images\tz.img (
%fastboot% flash tz_ab images\tz.img
)
if exist images\tz_ac_config.img (
%fastboot% flash tz_ac_config_ab images\tz_ac_config.img
)
if exist images\tz_qti_config.img (
%fastboot% flash tz_qti_config_ab images\tz_qti_config.img
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
if exist images\vendor_boot.img (
%fastboot% flash vendor_boot_ab images\vendor_boot.img
)
if exist images\vm-bootsys.img (
%fastboot% flash vm-bootsys_ab images\vm-bootsys.img
)
if exist images\xbl.img (
%fastboot% flash xbl_ab images\xbl.img
)
if exist images\xbl_ac_config.img (
%fastboot% flash xbl_ac_config_ab images\xbl_ac_config.img
)
if exist images\xbl_config.img (
%fastboot% flash xbl_config_ab images\xbl_config.img
)
if exist images\xbl_ramdump.img (
%fastboot% flash xbl_ramdump_ab images\xbl_ramdump.img
)
if exist images\boot.img (
%fastboot% flash boot_ab images\boot.img
)
if exist images\init_boot.img (
%fastboot% flash init_boot_ab images\init_boot.img
)
set r=
if /i "%CHON2%"=="m" set r=magisk
if /i "%CHON2%"=="k" set r=ksu
if defined r if exist "images\%b%_%r%.img" (
%fastboot% flash %b%_ab "images\%b%_%r%.img"
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
%fastboot% flash recovery_ab images\recovery.img
)
if exist images\super.img (
echo. 3. Cập nhật phân vùng super... (Tập tin này rất lớn. Vui lòng chờ!)
echo.    Flashing the super partition... (This file is very large, please wait!)
%fastboot% flash super images\super.img
)
if /i "%CHON1%"=="y" (
%fastboot% erase userdata
%fastboot% erase metadata
)
%fastboot% set_active a
%fastboot% reboot
echo.
pause