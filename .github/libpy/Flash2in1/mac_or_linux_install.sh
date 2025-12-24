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
    [[ -z $(command -v zstd) ]] && brew install zstd
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
    echo
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
    if [ -f "images/abl.elf" ]; then
        $fastboot flash abl images/abl.elf
        $fastboot flash ablbak images/abl.elf
    fi
    if [ -f "images/aop.mbn" ]; then
        $fastboot flash aop images/aop.mbn
        $fastboot flash aopbak images/aop.mbn
    fi
    if [ -f "images/BTFM.bin" ]; then
        $fastboot flash bluetooth images/BTFM.bin
    fi
    if [ -f "images/cmnlib64.mbn" ]; then
        $fastboot flash cmnlib64 images/cmnlib64.mbn
        $fastboot flash cmnlib64bak images/cmnlib64.mbn
    fi
    if [ -f "images/cmnlib.mbn" ]; then
        $fastboot flash cmnlib images/cmnlib.mbn
        $fastboot flash cmnlibbak images/cmnlib.mbn
    fi
    if [ -f "images/devcfg.mbn" ]; then
        $fastboot flash devcfg images/devcfg.mbn
        $fastboot flash devcfgbak images/devcfg.mbn
    fi
    if [ -f "images/dspso.bin" ]; then
        $fastboot flash dsp images/dspso.bin
    fi
    if [ -f "images/dtbo.img" ]; then
        $fastboot flash dtbo images/dtbo.img
    fi
    if [ -f "images/featenabler.mbn" ]; then
        $fastboot flash featenabler images/featenabler.mbn
    fi
    if [ -f "images/hyp.mbn" ]; then
        $fastboot flash hyp images/hyp.mbn
        $fastboot flash hypbak images/hyp.mbn
    fi
    if [ -f "images/km4.mbn" ]; then
        $fastboot flash keymaster images/km4.mbn
    fi
    if [ -f "images/NON-HLOS.bin" ]; then
        $fastboot flash modem images/NON-HLOS.bin
    fi
    if [ -f "images/qupv3fw.elf" ]; then
        $fastboot flash qupfw images/qupv3fw.elf
        $fastboot flash qupfwbak images/qupv3fw.elf
    fi
    if [ -f "images/tz.mbn" ]; then
        $fastboot flash tz images/tz.mbn
        $fastboot flash tzbak images/tz.mbn
    fi
    if [ -f "images/uefi_sec.mbn" ]; then
        $fastboot flash uefisecapp images/uefi_sec.mbn
    fi
    if [ -f "images/vbmeta.img" ]; then
        $fastboot flash vbmeta images/vbmeta.img
    fi
    if [ -f "images/vbmeta_system.img" ]; then
        $fastboot flash vbmeta_system images/vbmeta_system.img
    fi
    if [ -f "images/xbl_config_4.elf" ]; then
        $fastboot flash xbl_config_4 images/xbl_config_4.elf
    fi
    if [ -f "images/xbl_config_5.elf" ]; then
        $fastboot flash xbl_config_5 images/xbl_config_5.elf
    fi
    if [ -f "images/xbl_4.elf" ]; then
        $fastboot flash xbl_4 images/xbl_4.elf
    fi
    if [ -f "images/xbl_5.elf" ]; then
        $fastboot flash xbl_5 images/xbl_5.elf
    fi
    if [ -f "images/storsec.mbn" ]; then
        $fastboot flash storsec images/storsec.mbn
        $fastboot flash storsecbak images/storsec.mbn
    fi
    if [ -f "images/logo.img" ]; then
        $fastboot flash logo images/logo.img
    fi
 
    if [ "$choice2" == 'Y' ] || [ "$choice2" == 'y' ]; then
        $fastboot flash boot images/boot_magisk.img
    elif [ "$choice2" == 'N' ] || [ "$choice2" == 'n' ]; then
        $fastboot flash boot images/boot.img
    fi

    if [ -f "images/super.img" ]; then
        echo 'Bắt đầu flash super. Tệp này lớn và có thể mất nhiều thời gian tùy thuộc vào cấu hình máy tính của bạn. (Start flashing super. This file is large and may take a long time depending on your computer configuration.)'
        $fastboot flash super images/super.img
    fi
    
    if [ -f "images/recovery.img" ]; then 
        $fastboot flash recovery images/recovery.img
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
    $fastboot reboot
    exit
}
q1
