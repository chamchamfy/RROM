sudo rm -rf /usr/share/dotnet
sudo rm -rf /opt/ghc
sudo rm -rf "/usr/local/share/boost"
sudo rm -rf "$AGENT_TOOLSDIRECTORY"

export TOME="$GITHUB_WORKSPACE"
export PATH="$TOME/.github/bin:$PATH"
chmod -R 777 $TOME/.github/bin/* >/dev/null
chmod -R 777 $TOME/.github/*.sh >/dev/null
sed -i -e 's/\r$//' $TOME/.github/bin/Rebuild >/dev/null 

echo "▼ Tên máy chủ"
uname -a
echo

sudo apt-get update > /dev/null
sudo apt-get install wget curl zstd binutils e2fsprogs erofs-utils simg2img img2simg zipalign > /dev/null
pip3 install protobuf bsdiff4 six crypto construct google docopt pycryptodome > /dev/null

echo "protobuf<=3.20.1" > requirements.txt
pip3 install -r requirements.txt > /dev/null

echo "- Chạy thử nghiệm lệnh"

TOME="$GITHUB_WORKSPACE"
Phanvung="system system_a vendor vendor_a product product_a system_ext odm odm_a mi_ext mi_ext_a system_dlkm system_dlkm_a vendor_dlkm vendor_dlkm_a"; 
danhsach='system vendor system_ext product odm mi_ext system_dlkm vendor_dlkm'; 
Boot="boot boot_a vendor_boot vendor_boot_a"; 

User="User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
Xem() { curl -s -L -G -N -H "$User" --connect-timeout 20 "$1"; }
Taive() { curl -s -L -k -H "$User" --connect-timeout 20 "$1" -o "$2"; }
Taiver() { curl -S -k "$1" -o "$2"; }
Taivewget() { wget "$1" -O "$2"; }
Taivewgetr() { wget --no-check-certificate "$1" -O "$2"; }
mkdir -p $TOME/{tmp,Unpack,Repack,Unzip,Payload,Super,Apk,Mod/tmp,VH,Up} 

Taidulieu() { 

#Tenrom=${URL##*/} && Tenr=${Tenrom%.*} && Dinhdang=${URL##*.}; 
URL="https://bn.d.miui.com/OS1.0.20.0.UKDTWXM/miui_VILITWGlobal_OS1.0.20.0.UKDTWXM_071a550596_14.0.zip"
echo "- Link Rom: $URL"

echo "- Tải về" 

aria2c --continue=true -x16 -s16 -d "$TOME" -o "rom.zip" "$URL"
#Taiver "$URL" "$TOME/rom1.zip" 
#Taive "$URL" "$TOME/rom2.zip"

du -m $TOME/rom.zip | awk '{print $1}'
file $TOME/rom.zip
TROM="${URL##*/}.zip"

NEMROM=RROM_${TROM}
echo "NEMROM=$NEMROM" >> $GITHUB_ENV


echo "Tên rom: $NEMROM"
#mv -f $TOME/rom.x $TOME/$NEMROM

echo "- Giải nén rom" 
echo "$(file $TOME/rom.zip)"
if [ "$(file $TOME/rom.zip | grep 'Zip archive')" -o "$(file $TOME/rom.zip | grep 'Java archive')" ]; then echo " Giải nén: $(ls $TOME/rom.zip)"
 unzip -qo "$TOME/rom.zip" -d "$TOME/Unzip" 2>/dev/null
 cp -rf $TOME/Unzip/META-INF/com/android $TOME/.github/libpy/Flash2in1/META-INF/com 2>/dev/null
 elif [ "$(file $TOME/rom.zip | grep 'gzip compressed')" ]; then
 tar -xvf "$TOME/rom.zip" -C "$TOME/Unzip"
 else
 bug "- Rom không phải file zip hoặc tgz, gz"
fi 
}

Taidulieu
ls $TOME/Unzip
#. $TOME/Option.md
echo "- Kết thúc" 
