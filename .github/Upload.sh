# kakathic & chamchamfy
. .github/Function.sh
cd $TOME/.github/libpy/Flash2in1

if [ -e $TOME/ok ]; then
# Nén rom zip
Chatbot "Nén ROM: $NEMEROM"
zip -qr $TOME/$NEMEROM *

echo
Chatbot '- ROM đang tải lên sever vui lòng chờ...'

sv1() { 
#url10=$(curl -s https://api.gofile.io/servers | jq -r '.data.serversAllZone' | grep -m10 'name' | awk -F'"' '{print $4}')
url1=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers' | grep -m1 'name' | awk -F'"' '{print $4}')
url2=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers' | grep -m2 'name' | awk -F'"' '{print $4}')
eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url1.gofile.io/uploadFile' > $TOME/1.json" || eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url2.gofile.io/uploadFile' > $TOME/1.json"
LINKROM1=$(cat "$TOME/1.json" | jq -r .data.downloadPage)
}
sv2() {
APIK='440b20a6-90c0-40c7-9081-313b91c29456'
eval "curl -T '$TOME/$NEMEROM' -u :'$APIK' 'https://pixeldrain.com/api/file/' > $TOME/1.json"
#curl -1 -v -k "https://pixeldrain.com/api/user/files" --user "*:*" -T "$TOME/$NEMEROM" 
LINKROM2="https://pixeldrain.com/u/$(cat "$TOME/1.json" | jq -r .id)"
}
sv3() {
#https://file.io#M4GB
LINKROM3=$(cat "$TOME/1.json" | jq -r .link)
}
sv4() {
#https://filebin.net#6D
LINKROM4=$(curl -s 'https://filebin.net' | grep -m1 'filebin.net/' | awk -F'"' '{print $4}')
curl -F "file=@$TOME/$NEMEROM" "$LINKROM4"
}
sv5() {
#https://easyupload.io#30D
LINKROM5=$(grep -m1 'text:' $TOME/1.json | awk -F'"' '{print $2}')
}
sv6() {
#https://wetransfer.com#M2GB#7D
LINKROM6=$(grep -m1 'wetransfer.com/' $TOME/1.json | awk -F'"' '{print $4}')
}
sv7() {
#https://filetransfer.io#21D#M6GB
LINKROM7=$(grep -m1 'filetransfer.io/' $TOME/1.json | awk -F'"' '{print $4}')
}
svsfg() {
tailenr() { TTK=$4; curl -1 -v -k "sftp://$1/$4/$NEMEROM" --user "$2:$3" -T "$TOME/$NEMEROM"; }
. $TOME/mk.sh
tailenr "frs.sourceforge.net:/home/frs/project" "$TND" "$MK" "rroms"
LINKROMSFG="https://sourceforge.net/projects/$TTK/files/$NEMEROM"
}

sv1 && Chatbot " Link tải về: $LINKROM1"
sv2 && Chatbot " Link tải về: $LINKROM2"
#sv4 && Chatbot " Link tải về: $LINKROM4"
if [ "$SEVERUP" = 1 ]; then Chatbot '- Tải ROM lên máy chủ sourceforge.net ...' && svsfg; fi
 
# Link download 
echo
closechat "Tạo rom thành công <br/><br/>Link Download: "$LINKROM1" <br/><br/>Link Download: "$LINKROM2" <br/><br/>Link Download (sourceforge.net): $LINKROMSFG"; 
#addlabel "Hoàn thành"
else
closechat "Tạo rom thất bại, Xem log: 📱[Actions runs](https://github.com/chamchamfy/RROM/actions/runs/$GITHUB_RUN_ID)"
#addlabel "Thất bại"
fi

#removelabel "Build"
#removelabel "Wait"
