cd $(dirname $0)
clear

not_support() {
    echo 'Hệ thống của bạn chưa được hỗ trợ, Vui lòng chọn hệ thống khác để flash! (Your system is not supported yet, Please choose another system to flash!)'
    exit
}

if [ "$(uname)" == "Linux" ]; then
    systemType=linux
elif [ "$(uname)" == "Darwin" ]; then
    systemType=darwin
    [[ -z "$(command -v zstd)" ]] && brew install zstd
else
    not_support
fi

fastboot="bin/$systemType/all/fastboot"
thietbi=kb
[ -f "bin/$systemType/all/zstd" ] && zst="bin/$systemType/all/zstd" || zst=zstd
device=$($fastboot getvar product 2>&1 | grep -F "product:" | tr -s " " | cut -d " " -f 2)
[ -z "$device" ] && device="unknown"
[ "$device" != "$thietbi" ] && echo "Dành cho thiết bị (Compatible devices): $thietbi" && echo "Thiết bị của bạn (Your device): $device" && exit 1

if [ -f "images/super.img.zst" ]; then
    echo 'Đang chuẩn bị... (Preparing...)'
    echo '- Bắt đầu chuyển đổi super. Có thể mất nhiều thời gian, tùy thuộc vào cấu hình máy tính của bạn. (- Start converting super partition. It may take a long time, depending on your computer configuration.)'
    read -p "Lưu ý: Hãy đảm bảo rằng dung lượng còn lại của phân vùng hiện tại của bạn lớn hơn 10GB, nếu không quá trình chuyển đổi super sẽ không thành công. Bấm phím bất kỳ để tiếp tục... (Note: Please ensure that the free size of the current partition is greater than 10GB, otherwise the super conversion will fail. Press any key to continue...)" readtemp
    $zst --rm -d images/super.img.zst -o images/super.img
    if [ $? -ne 0 ]; then
        read -p "Chuyển đổi bị lỗi, nhấn phím bất kì để thoát... (Conversion process error, press any key to exit...)" readtemp
        exit
    fi
    echo 'Chuẩn bị hoàn thành... (Preparation completed...)'
fi

q1() {
    read -p "1. Cài đặt lần đầu sẽ xóa dữ liệu và bộ nhớ trong. Bạn đồng ý không？ (1. Flashing the first time will erase data and internal memory. Do you agree?) (Y/N) " choice1
    if [ "$choice1" == 'Y' ] || [ "$choice1" == 'y' ] || [ "$choice1" == 'N' ] || [ "$choice1" == 'n' ]; then
        q2
    else
        q1
    fi
}

q2() {
    read -p "2. Bạn muốn cài đặt boot_magisk.img (ROOT) nếu có?  (2. Do you want to flash boot_magisk.img (ROOT))?(Y/N) " choice2
    if [ "$choice2" == 'Y' ] || [ "$choice2" == 'y' ] || [ "$choice2" == 'N' ] || [ "$choice2" == 'n' ]; then
        main
    else
        q2
    fi
}

main() {
    if [ -f "images/abl.img" ]; then
        $fastboot flash abl_ab images/abl.img
    fi
    if [ -f "images/aop_config.img" ]; then
        $fastboot flash aop_config_ab images/aop_config.img
    fi
    if [ -f "images/aop.img" ]; then
        $fastboot flash aop_ab images/aop.img
    fi
    if [ -f "images/bluetooth.img" ]; then
        $fastboot flash bluetooth_ab images/bluetooth.img
    fi
    if [ -f "images/cmnlib64.img" ]; then
        $fastboot flash cmnlib64_ab images/cmnlib64.img
    fi
    if [ -f "images/cmnlib.img" ]; then
        $fastboot flash cmnlib_ab images/cmnlib.img
    fi
    if [ -f "images/cpucp.img" ]; then
        $fastboot flash cpucp_ab images/cpucp.img
    fi
    if [ -f "images/cpucp_dtb.img" ]; then
        $fastboot flash cpucp_dtb images/cpucp_dtbl.img
    fi
    if [ -f "images/countrycode.img" ]; then
        $fastboot flash countrycode_ab images/countrycode.img
    fi
    if [ -f "images/devcfg.img" ]; then
        $fastboot flash devcfg_ab images/devcfg.img
    fi
    if [ -f "images/dsp.img" ]; then
        $fastboot flash dsp_ab images/dsp.img
    fi
    if [ -f "images/dtbo.img" ]; then
        $fastboot flash dtbo_ab images/dtbo.img
    fi
    if [ -f "images/featenabler.img" ]; then
        $fastboot flash featenabler_ab images/featenabler.img
    fi
    if [ -f "images/hyp.img" ]; then
        $fastboot flash hyp_ab images/hyp.img
    fi
    if [ -f "images/imagefv.img" ]; then
        $fastboot flash imagefv_ab images/imagefv.img
    fi
    if [ -f "images/keymaster.img" ]; then
        $fastboot flash keymaster_ab images/keymaster.img
    fi
    if [ -f "images/modem.img" ]; then
        $fastboot flash modem_ab images/modem.img
    fi
    if [ -f "images/modemfirmware.img" ]; then
        $fastboot flash modemfirmware_ab images/modemfirmware.img
    fi
    if [ -f "images/multiimgqti.img" ]; then
        $fastboot flash multiimgqti_ab images/multiimgqti.img
    fi
    if [ -f "images/qupfw.img" ]; then
        $fastboot flash qupfw_ab images/qupfw.img
    fi
    if [ -f "images/shrm.img" ]; then
        $fastboot flash shrm_ab images/shrm.img
    fi
    if [ -f "images/spuservice.img" ]; then
        $fastboot flash spuservice_ab images/spuservice.img
    fi
    if [ -f "images/tz.img" ]; then
        $fastboot flash tz_ab images/tz.img
    fi
    if [ -f "images/uefisecapp.img" ]; then
        $fastboot flash uefisecapp_ab images/uefisecapp.img
    fi
    if [ -f "images/uefi.img" ]; then
        $fastboot flash uefi_ab images/uefi.img
    fi
    if [ -f "images/vbmeta.img" ]; then
        $fastboot flash vbmeta_ab images/vbmeta.img
    fi
    if [ -f "images/vbmeta_system.img" ]; then
        $fastboot flash vbmeta_system_ab images/vbmeta_system.img
    fi
    if [ -f "images/vbmeta_vendor.img" ]; then
        $fastboot flash vbmeta_vendor_ab images/vbmeta_vendor.img
    fi
    if [ -f "images/vendor_boot.img" ]; then
        $fastboot flash vendor_boot_ab images/vendor_boot.img
    fi
    if [ -f "images/vm-bootsys.img" ]; then
        $fastboot flash vm-bootsys_ab images/vm-bootsys.img
    fi
    if [ -f "images/xbl_ramdump.img" ]; then
        $fastboot flash xbl_ramdump_ab images/xbl_ramdump.img
    fi
    if [ -f "images/xbl_config.img" ]; then
        $fastboot flash xbl_config_ab images/xbl_config.img
    fi
    if [ -f "images/xbl.img" ]; then
        $fastboot flash xbl_ab images/xbl.img
    fi
    if [ -f "images/init_boot.img" ]; then
        $fastboot flash init_boot_ab images/init_boot.img
    fi

    if [ "$choice2" == 'Y' ] || [ "$choice2" == 'y' ]; then
        $fastboot flash boot_ab images/boot_magisk.img
    elif [ "$choice2" == 'N' ] || [ "$choice2" == 'n' ]; then
        $fastboot flash boot_ab images/boot.img
    fi

    if [ -f "images/super.img" ]; then
        echo 'Bắt đầu flash super. Tệp này lớn và có thể mất nhiều thời gian tùy thuộc vào cấu hình máy tính của bạn. (Start flashing super. This file is large and may take a long time depending on your computer configuration.)'
        $fastboot flash super images/super.img
    fi

    if [ -f "images/recovery.img" ]; then 
        $fastboot flash recovery_ab images/recovery.img
    fi

    if [ -f "images/cust.img" ]; then 
        $fastboot flash cust images/cust.img
    fi
    
    if [ -f "images/persist.img" ]; then 
        $fastboot flash persistbak images/persist.img
        $fastboot flash persist images/persist.img
    fi
    
    if [ -f "images/splash.img" ]; then 
        $fastboot flash splash images/splash.img
    fi

    if [ "$choice1" == 'Y' ] || [ "$choice1" == 'y' ]; then
        $fastboot erase userdata
        $fastboot erase metadata
    fi
    
    $fastboot set_active a
    $fastboot reboot
    exit
}
q1
