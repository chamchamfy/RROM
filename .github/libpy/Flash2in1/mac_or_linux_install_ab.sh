cd $(dirname $0)
clear

not_support() {
    echo '	Hệ thống của bạn chưa được hỗ trợ, Vui lòng chọn hệ thống khác để flash! 
	(Your system is not supported yet, Please choose another system to flash!)'
    exit
}

if [ "$(uname)" == "Linux" ]; then
    Loai=linux
elif [ "$(uname)" == "Darwin" ]; then
    Loai=darwin
    [[ -z "$(command -v zstd)" ]] && brew install zstd
else
    not_support
fi

fastboot="bin/$Loai/all/fastboot"
thietbi=kb
[ -f "bin/$Loai/all/zstd" ] && zst="bin/$Loai/all/zstd" || zst=zstd
R=$($fastboot getvar all 2>&1 | grep "partition-size:init_boot")
device=$($fastboot getvar product 2>&1 | grep -F "product:" | tr -s " " | cut -d " " -f 2)
[ -z "$device" ] && device="unknown"
[ "$device" != "$thietbi" ] && echo "Dành cho thiết bị (Compatible devices): $thietbi" && echo "Thiết bị của bạn (Your device): $device" && exit 1

if [ -f "images/super.img.zst" ]; then
    echo 'Đang chuẩn bị... (Preparing...)'
    echo '- Bắt đầu chuyển đổi super. Có thể mất nhiều thời gian, tùy thuộc vào cấu hình máy tính của bạn.
 (- Converting super partition. This may take some time depending on your PC hardware.)'
    echo '- Lưu ý: Ổ đĩa cần trống tối thiểu 10GB, nếu không quá trình chuyển đổi super sẽ lỗi. Bấm phím bất kỳ để tiếp tục...
 (- Note: At least 10GB of free disk space is required, otherwise the conversion will fail. Press any key to continue...)'
    read -p "Bấm phím bất kỳ để tiếp tục... (Press any key to continue...)" readtemp
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
    read -p "2. Bạn muốn cài đặt ROOT nếu có?  (2. Do you want to flash ROOT?) (Y/N) " choice2
    if [ "$choice2" == 'Y' ] || [ "$choice2" == 'y' ] || [ "$choice2" == 'N' ] || [ "$choice2" == 'n' ]; then
        main
    else
        q2
    fi
}

main() {
  for ten in abl aop aop_config bluetooth cmnlib64 cmnlib countrycode cpucp cpucp_dtb dcp devcfg dsp dtbo featenabler hyp hyp_ac_config idmanager imagefv init_boot keymaster modem modemfirmware modemfirmware_ww multqti pdp pdp_cdb pvmfw qtvm_dtbo qupfw secretkeeper shrm soccp soccp_dcd soccp_debug spuservice tme_config tme_fw tme_seq_patch tz tz_ac_config tz_qti_config uefi uefisecapp vbmeta vbmeta_system vendor_boot vm-bootsys xbl xbl_ac_config xbl_config xbl_ramdump boot cust splash recovery; do 
    if [ -f "images/${ten}.img" ]; then 
      echo " Cập nhật phân vùng $ten ..."
      $fastboot flash ${ten}_ab images/${ten}.img || { echo "Lỗi flash: $ten !"; exit 1; }
    fi
  done

    if [ "$choice2" == 'Y' ] || [ "$choice2" == 'y' ]; then
     echo " Đang flash root ..."
     if [ -n "$R" ]; then 
      [ -f "images/init_boot_magisk.img" ] && { $fastboot flash init_boot_ab images/init_boot_magisk.img || echo "Lỗi flash: init_boot_magisk.img!"; exit 1; }
      [ -f "images/init_boot_ksu.img" ] && { $fastboot flash init_boot_ab images/init_boot_ksu.img || echo "Lỗi flash: init_boot_ksu.img!"; exit 1; }
     else
      [ -f "images/boot_magisk.img" ] && { $fastboot flash boot_ab images/boot_magisk.img || echo "Lỗi flash: boot_magisk.img!"; exit 1; }
      [ -f "images/boot_ksu.img" ] && { $fastboot flash boot_ab images/boot_ksu.img || echo "Lỗi flash: boot_ksu.img!"; exit 1; }
     fi
    fi

    if [ -f "images/cust.img.0" ]; then 
      $fastboot flash cust images/cust.img.0 || { echo "Lỗi flash: cust.img.0 !"; exit 1; }
      $fastboot flash cust images/cust.img.1 || { echo "Lỗi flash: cust.img.1 !"; exit 1; }
    fi
#    if [ -f "images/persist.img" ]; then 
#      $fastboot flash persistbak images/persist.img
#      $fastboot flash persist images/persist.img
#    fi
    if [ -f "images/super.img" ]; then
      echo 'Bắt đầu flash super. Tệp này lớn và có thể mất nhiều thời gian, vui lòng chờ. (Flashing the super partition... This file is very large, please wait!)'
      $fastboot flash super images/super.img || { echo "Lỗi flash: super.img!"; exit 1; }
    fi
    if [ "$choice1" == 'Y' ] || [ "$choice1" == 'y' ]; then
      $fastboot erase userdata
      $fastboot erase metadata
    fi

    $fastboot set_active a
    $fastboot reboot
    sleep 3
    exit
}
q1
