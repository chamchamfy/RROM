# kakathic & chamchamfy
. .github/Function.sh
cd $TOME/.github/libpy/Flash2in1

if [ -e $TOME/ok ]; then
# Nén rom zip
Chatbot "Nén ROM: $NEMEROM"
zip -qr $TOME/$NEMEROM *

echo
Chatbot '- ROM đang tải lên sever vui lòng chờ...'

if [ "$SEVERUP" = 1 ];then
APIK='440b20a6-90c0-40c7-9081-313b91c29456'
eval "curl -T '$TOME/$NEMEROM' -u :'$APIK' 'https://pixeldrain.com/api/file/' > $TOME/1.json"
#curl -1 -v -k "https://pixeldrain.com/api/user/files" --user "*:*" -T "$TOME/$NEMEROM" 
LINKROM="https://pixeldrain.com/u/$(cat "$TOME/1.json" | jq -r .id)"
else
#url10=$(curl -s https://api.gofile.io/servers | jq -r '.data.serversAllZone' | grep -m10 'name' | awk -F'"' '{print $4}')
url1=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers' | grep -m1 'name' | awk -F'"' '{print $4}')
url2=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers' | grep -m2 'name' | awk -F'"' '{print $4}')
eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url1.gofile.io/uploadFile' > $TOME/1.json" || eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url2.gofile.io/uploadFile' > $TOME/1.json"
LINKROM=$(cat "$TOME/1.json" | jq -r .data.downloadPage)
fi
echo "Link download: $LINKROM"
Chatbot '- Tải ROM lên máy chủ khác...'
tailenr() { TTK=$4; curl -1 -v -k "sftp://$1/$4/$NEMEROM" --user "$2:$3" -T "$TOME/$NEMEROM"; }
. $TOME/mk.sh
tailenr "frs.sourceforge.net:/home/frs/project" "$TND" "$MK" "rroms"
echo "Link download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"
# Link download 
echo
closechat "Tạo rom thành công <br/><br/>Link Download: "$LINKROM" <br/><br/>Link Download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"
#addlabel "Hoàn thành"

else
closechat "Tạo rom thất bại, Xem log: 📱[Actions runs](https://github.com/chamchamfy/RROM/actions/runs/$GITHUB_RUN_ID)"
#addlabel "Thất bại"
fi

#removelabel "Build"
#removelabel "Wait"
