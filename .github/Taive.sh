# kakathic & chamchamfy
. .github/Function.sh

# Cài giờ Việt Nam
sudo apt-get install curl >/dev/null;
sudo cp /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime

# chat bot chào & thêm nhãn chờ
Chatbot 'Bắt đầu xây dựng, vui lòng chờ...<br/><br/>Sau khi xong link sẽ được gửi vào bài viết này, hoặc xem quá trình xây dựng 📱[Actions](https://github.com/chamchamfy/RROM/actions/runs/'$GITHUB_RUN_ID')<br/><br/>Muốn hủy quá trình xây dựng hãy ấn nút `Close Issues`, chỉ có thể hủy khi đang tải rom về.' >/dev/null 2>&1   
#addlabel "Wait"

# CÁC TÙY CHỌN WEB
Xem "https://github.com/chamchamfy/RROM/issues/$NUMBIE" > $TOME/1.ht

# get delete app
if [ "$(grep -cm1 'data-snippet-clipboard-copy-content=' $TOME/1.ht)" = 1 ]; then
grep -m1 'data-snippet-clipboard-copy-content="' $TOME/1.ht | awk -F'<' '{print $2}' | awk -F'"' '{print $6}' > $TOME/Delete_apps.md
fi
echo " Xoá app: $(cat $TOME/Delete_apps.md)"

# link url rom và size 
#URLKK="$(grep -m1 'dir="auto">Url:' $TOME/1.ht | grep -o 'Url:.*<' | sed 's|Url:<||' | cut -d '"' -f2)"
#SIZEKK="$(grep -o 'dir="auto">.*GB' $TOME/1.ht | cut -d '>' -f2 | sed 's|GB||')"
URLKK="$(grep -m1 'dir="auto">Url:' $TOME/1.ht | awk -F'"' '{print $4}')"

# Thêm recovery mod
[ -n "$(grep 'Không thêm' $TOME/1.ht)" ] && RECOVERYMOD="0"
[ -n "$(grep 'OFOX' $TOME/1.ht)" ] && RECOVERYMOD="OFOX"
[ -n "$(grep 'TWRP' $TOME/1.ht)" ] && RECOVERYMOD="TWRP"
[ -n "$(grep 'PBRP' $TOME/1.ht)" ] && RECOVERYMOD="PBRP"
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
[ -n "$(grep 'Mặc định' $TOME/1.ht)" ] && DGPU="0"
[ -n "$(grep 'Phiên bản GPU 725' $TOME/1.ht)" ] && DGPU="725"
[ -n "$(grep 'Phiên bản GPU 615' $TOME/1.ht)" ] && DGPU="615"
GITENV AGPU $DGPU

# Tùy chọn loại hệ thống
[ -n "$(grep 'Theo hệ thống' $TOME/1.ht)" ] && DDPV="0"
[ -n "$(grep 'Chỉ đọc' $TOME/1.ht)" ] && DDPV="erofs"
[ -n "$(grep 'Cho phép ghi đọc' $TOME/1.ht)" ] && DDPV="ext4"
GITENV Loaihethong $DDPV

# Thêm tên tác giả khi flash Rom
GITENV Tacgia "chamchamfy"

# Chọn sv upload
GITENV SEVERUP "$(checktc Sourceforge)"

# check url
GITENV URL $URLKK
if [ "$URL" ]; then

(
sudo apt-get update >/dev/null
sudo apt-get install zstd binutils e2fsprogs erofs-utils simg2img img2simg zipalign f2fs-tools p7zip >/dev/null
pip3 install protobuf bsdiff4 six crypto construct google docopt pycryptodome >/dev/null
echo "protobuf<=3.20.1" > requirements.txt
pip3 install -r requirements.txt >/dev/null;
) & ( 

Chatbot "- Bắt đầu tải ROM: $URL ...";
Taiver "$URL" "$TOME/rom.x" 
[ ! -f "$TOME/rom.x" ] && Taive "$URL" "$TOME/rom.x"
[ -f "$TOME/rom.x" -a "$(du -m $TOME/rom.x | awk '{print $1}')" -lt 1024 ] && Taive "$URL" "$TOME/rom.x"


) & (
# Tải rom và tải file khác
while true; do
if [ "$(gh issue view $NUMBIE | grep -cm1 CLOSED)" == 1 ]; then
Chatbot "Đã nhận được lệnh hủy quá trình."
cancelrun
exit 0
else
[ -e "$TOME/rom.x" ] && break
sleep 10
fi
done
)

echo
Chatbot "- Giải nén ROM ${URL##*/} ..."

if [ -f "$TOME/rom.x" ]; then
 if [ -n "$(xxd -l 4 -c 4 $TOME/rom.x | grep '504b')" ]; then
#mv -f "$TOME/rom.x" "$TOME/rom.zip"
unzip -qo "$TOME/rom.x" -d "$TOME/Unzip" 2>/dev/null
cp -rf $TOME/Unzip/META-INF/com/android $TOME/.github/libpy/Flash2in1/META-INF/com 2>/dev/null
 elif [ -n "$(xxd -l 4 -c 4 $TOME/rom.x | grep '1f8b 0808')" ]; then 
#mv -f "$TOME/rom.x" "$TOME/rom.gz"
tar -xf "$TOME/rom.x" -C "$TOME/Unzip"
 elif [ -n "$(xxd -l 4 -c 4 $TOME/rom.x | grep '1f8b 0880')" ]; then 
#mv -f "$TOME/rom.x" "$TOME/rom.tgz"
tar -xf "$TOME/rom.x" -C "$TOME/Unzip"
 else bug "- Rom không phải file zip hoặc tgz, gz"
 fi
NEMEROM="RROM_${DDPV}_${URL##*/}.zip"
echo "NEMEROM=$NEMEROM" >> $GITHUB_ENV

# Xoá tập tin rom sau khi giải nén 
sudo rm -f $TOME/rom.x 2>/dev/null
else
bug "- Liên kết tải lỗi..."
fi
