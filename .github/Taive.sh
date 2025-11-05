# kakathic & chamchamfy
. .github/Function.sh
GOME="$GITHUB_WORKSPACE"

# Cài giờ Việt Nam
sudo apt-get install curl >/dev/null;
sudo cp /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime

# chat bot chào & thêm nhãn chờ
Chatbot 'Bắt đầu xây dựng, vui lòng chờ...<br/><br/>Sau khi xong link sẽ được gửi vào bài viết này, hoặc xem quá trình xây dựng 📱[Actions](https://github.com/chamchamfy/RROM/actions/runs/'$GITHUB_RUN_ID')<br/><br/>Muốn hủy quá trình xây dựng hãy ấn nút `Close Issues`, chỉ có thể hủy khi đang tải rom về.' >/dev/null 2>&1   
#addlabel "Wait"

# CÁC TÙY CHỌN WEB
Xem "https://github.com/chamchamfy/RROM/issues/$NUMBIE" > $GOME/1.ht

# get delete app
if [ "$(grep -cm1 'data-snippet-clipboard-copy-content=' $GOME/1.ht)" = 1 ]; then
grep -m1 'data-snippet-clipboard-copy-content="' $GOME/1.ht | awk -F'<' '{print $2}' | awk -F'"' '{print $6}' > $GOME/Delete_apps.md
fi
echo " Xoá app: $(cat $GOME/Delete_apps.md)"

# link url rom và size 
#URLKK="$(grep -m1 'dir="auto">Url:' $GOME/1.ht | grep -o 'Url:.*<' | sed 's|Url:<||' | cut -d '"' -f2)"
#SIZEKK="$(grep -o 'dir="auto">.*GB' $GOME/1.ht | cut -d '>' -f2 | sed 's|GB||')"
URLKK="$(grep -m1 'dir="auto">Url:' $GOME/1.ht | awk -F'"' '{print $4}')"

# Thêm recovery mod
[ -n "$(grep 'Không thêm' $GOME/1.ht)" ] && RECOVERYMOD="0"
[ -n "$(grep 'OFOX' $GOME/1.ht)" ] && RECOVERYMOD="OFOX"
[ -n "$(grep 'TWRP' $GOME/1.ht)" ] && RECOVERYMOD="TWRP"
[ -n "$(grep 'PBRP' $GOME/1.ht)" ] && RECOVERYMOD="PBRP"
GITENV MREC $RECOVERYMOD

# Thêm Các tùy chọn: 1=Bật, 0=Tắt
GITENV TTV "$(checkbox 'Thêm Tiếng Việt')"
GITENV GAPP "$(checkbox 'Thêm GAPP')"
GITENV HK "$(checkbox 'Thêm âm thanh HARMAN KARDON')"
GITENV Vsys "$(checkbox 'Vá hệ thống')"
GITENV Vccg "$(checkbox 'Vá chứng chỉ')"
GITENV Vfstab "$(checkbox 'Bỏ mã hoá Rom')"
GITENV Thucthi "$(checkbox 'Vá Permissive')"
GITENV NRW "$(checkbox 'Cho phép đọc ghi vài phân vùng')"
GITENV AP "$(checkbox 'Thêm APEX')"
GITENV APPM "$(checkbox 'Thêm ứng dụng đã Mod')"

# Tùy chọn Adreno GPU Driver
[ -n "$(grep 'Mặc định' $GOME/1.ht)" ] && DGPU="0"
[ -n "$(grep 'Phiên bản GPU 725' $GOME/1.ht)" ] && DGPU="725"
[ -n "$(grep 'Phiên bản GPU 615' $GOME/1.ht)" ] && DGPU="615"
GITENV AGPU $DGPU

# Tùy chọn loại hệ thống
[ -n "$(grep 'Theo hệ thống' $GOME/1.ht)" ] && DDPV="0"
[ -n "$(grep 'Chỉ đọc' $GOME/1.ht)" ] && DDPV="erofs"
[ -n "$(grep 'Cho phép ghi đọc' $GOME/1.ht)" ] && DDPV="ext4"
GITENV Loaihethong $DDPV

# Gắn lên git env
GITENV URL $URLKK
GITENV NEMEROM "RROM_${DDPV}_${URL##*/}.zip"
#GITENV DINHDANG "${URL##*.}"

# Thêm tên tác giả khi flash Rom
GITENV Tacgia "chamchamfy"

# Chọn sv upload
GITENV SEVERUP "$(checktc Sourceforge)"

# check url
if [ "$URL" ]; then

(
sudo apt-get update >/dev/null
sudo apt-get install zstd binutils e2fsprogs erofs-utils simg2img img2simg zipalign f2fs-tools p7zip >/dev/null
pip3 install protobuf bsdiff4 six crypto construct google docopt pycryptodome >/dev/null
echo "protobuf<=3.20.1" > requirements.txt
pip3 install -r requirements.txt >/dev/null;
) & ( 

Chatbot "- Bắt đầu tải ROM: $URL ...";
#Taiver "$URL" "$GOME/rom.zip" 
#[ "$(du -m $GOME/rom.zip | awk '{print $1}')" -lt 1024 ] && Taive "$URL" "$GOME/rom.zip"
aria2c -x 16 -s 16 -d "$GOME" -o "rom.zip" "$URL"
mv -f "$GOME/rom.zip" "$GOME/$NEMEROM"
[ -e "$GOME/$NEMEROM" ] || touch "$GOME/lag"

) & (
# Tải rom và tải file khác
while true; do
if [ "$(gh issue view $NUMBIE | grep -cm1 CLOSED)" == 1 ]; then
Chatbot "Đã nhận được lệnh hủy quá trình."
cancelrun
exit 0
else
[ -e "$GOME/$NEMEROM" ] && break
[ -e "$GOME/lag" ] && break
sleep 10
fi
done
)

echo
Chatbot "- Giải nén ROM ${URL##*/} ..."

if [ -e "$GOME/$NEMEROM" ]; then
 [ -n "$(xxd -l 4 -c 4 $GOME/$NEMEROM | grep '504b')" ] && unzip -qo "$GOME/$NEMEROM" -d "$GOME/Unzip" 2>/dev/null
 [ -n "$(xxd -l 4 -c 4 $GOME/$NEMEROM | grep '1f8b')" ] && tar -xf "$GOME/$NEMEROM" -C "$GOME/Unzip" 2>/dev/null
 [ $? -ne 0 ] && bug "- Rom không phải file zip hoặc tgz, gz"
 cp -rf $GOME/Unzip/META-INF/com/android $GOME/.github/libpy/Flash2in1/META-INF/com 2>/dev/null
fi

# Xoá tập tin rom sau khi giải nén 
sudo rm -f $GOME/$NEMEROM 2>/dev/null
else
bug "- Liên kết tải lỗi..."
fi
