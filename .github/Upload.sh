# kakathic & chamchamfy
. .github/Function.sh
cd $TOME/.github/libpy/Flash2in1

if [ -e $TOME/ok ]; then
# Nén rom zip
Chatbot "Nén ROM: $NEMEROM"
zip -qr $TOME/$NEMEROM *

echo
Chatbot '- ROM đang tải lên sever vui lòng chờ...'

svsfg() {
tailenr() { TTK=$4; curl -1 -v -k "sftp://$1/$4/$NEMEROM" --user "$2:$3" -T "$TOME/$NEMEROM"; }
. $TOME/mk.sh
tailenr "frs.sourceforge.net:/home/frs/project" "$TND" "$MK" "rroms"
LINKROMSFG="https://sourceforge.net/projects/$TTK/files/$NEMEROM"
}
svpx() {
APIK='9e177f51-6e94-4e59-8aae-790a2f2b0c50'
eval "curl -T '$TOME/$NEMEROM' --connect-timeout 20 -u :'$APIK' 'https://pixeldrain.com/api/file/' > $TOME/1.json"
#curl -1 -v -k "https://pixeldrain.com/api/user/files" --user "*:*" -T "$TOME/$NEMEROM" 
LINKROMPX="https://pixeldrain.com/u/$(cat "$TOME/1.json" | jq -r .id)"
}
sv1() { 
url1=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers' | grep -m1 'name' | awk -F'"' '{print $4}')
url2=$(curl -s https://api.gofile.io/servers | jq -r '.data.serversAllZone' | grep -m1 'name' | awk -F'"' '{print $4}')
eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url1.gofile.io/uploadFile' > $TOME/1.json" || eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url2.gofile.io/uploadFile' > $TOME/1.json"
LINKROM1=$(cat "$TOME/1.json" | jq -r .data.downloadPage)
}
sv2() {
#https://file.io|4G
LINKROM2=$(cat "$TOME/1.json" | grep -m1 'link' $TOME/1.json | awk -F'"' '{print $4}')
}
sv3() {
#https://filebin.net|6D
LINKROM3=$(curl -s 'https://filebin.net' | grep -m1 'filebin.net/' | awk -F'"' '{print $4}')
curl -T "$TOME/$NEMEROM" "$LINKROM3/$NEMEROM"
}
sv4() {
#https://easyupload.io|30D
LINKROM4=$(grep -m1 'text:' $TOME/1.json | awk -F'"' '{print $2}')
}

sv1 && Chatbot " Link tải về: $LINKROM1"
#sv2 && Chatbot " Link tải về: $LINKROM2"
sv3 && Chatbot " Link tải về: $LINKROM3"
#sv4 && Chatbot " Link tải về: $LINKROM4"
if [ "$SEVERUP" = 1 ]; then Chatbot '- Tải ROM lên máy chủ sourceforge.net ...' && svsfg; else Chatbot '- Tải ROM lên máy chủ pixeldrain.com ...' && svpx; fi
 
# Link download 
closechat "Tạo rom thành công <br/><br/>Link Download (pixeldrain.com): "$LINKROMPX" <br/><br/>Link Download (sourceforge.net): "$LINKROMSFG" <br/><br/>Link Download: "$LINKROM1" <br/><br/>Link Download: "$LINKROM2" <br/><br/>Link Download: "$LINKROM3" <br/><br/>Link Download: "$LINKROM4" "; 
#addlabel "Hoàn thành"
else
closechat "Tạo rom thất bại, Xem log: 📱[Actions runs](https://github.com/chamchamfy/RROM/actions/runs/$GITHUB_RUN_ID)"
#addlabel "Thất bại"
fi

#removelabel "Build"
#removelabel "Wait"
