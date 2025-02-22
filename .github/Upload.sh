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

#if [ "$SEVERUP" = 1 ]; then sv2; else sv1; fi
sv1 && echo "Link download: $LINKROM1" && Chatbot " Link tải về: $LINKROM1"
sv2 && echo "Link download: $LINKROM2" && Chatbot " Link tải về: $LINKROM2"
 
Chatbot '- Tải ROM lên máy chủ khác...'
tailenr() { TTK=$4; curl -1 -v -k "sftp://$1/$4/$NEMEROM" --user "$2:$3" -T "$TOME/$NEMEROM"; }
. $TOME/mk.sh
tailenr "frs.sourceforge.net:/home/frs/project" "$TND" "$MK" "rroms"
echo "Link download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"
# Link download 
echo
if [ "$SEVERUP" = 1 ]; then 
closechat "Tạo rom thành công <br/><br/>Link Download: "$LINKROM2" <br/><br/>Link Download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"; 
else 
closechat "Tạo rom thành công <br/><br/>Link Download: "$LINKROM1" <br/><br/>Link Download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"; 
fi
#addlabel "Hoàn thành"
else
closechat "Tạo rom thất bại, Xem log: 📱[Actions runs](https://github.com/chamchamfy/RROM/actions/runs/$GITHUB_RUN_ID)"
#addlabel "Thất bại"
fi

#removelabel "Build"
#removelabel "Wait"
