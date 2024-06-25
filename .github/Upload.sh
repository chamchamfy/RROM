# kakathic
. .github/Function.sh
cd $TOME/.github/libpy/Flash2in1

if [ -e $TOME/ok ]; then
# Nén rom zip
Chatbot "Nén ROM: $NEMEROM"
zip -qr $TOME/$NEMEROM *

echo
Chatbot '- ROM đang tải lên sever vui lòng chờ...'

if [ "$SEVERUP" = 1 ];then
LINKROM="$(curl --upload-file "$TOME/$NEMEROM" https://transfer.sh)"
else
url2="$(curl -s https://api.gofile.io/getServer | jq -r .data.server)"
eval "curl -F 'file=@$TOME/$NEMEROM' 'https://$url2.gofile.io/uploadFile' > $TOME/1.json"
LINKROM="$(cat $TOME/1.json | jq -r .data.downloadPage)"
fi
Chatbot ' - Tải ROM lên sourceforge.net...'
tailensf() { TTK='rrom'; TND=$(echo 'Y2hhbWNoYW1meQ==' | base64 -d); MK=$(echo 'dHJ1b25nZ2lhbmc5MTA=' | base64 -d); curl -1 -v -k "sftp://frs.sourceforge.net:/home/frs/project/$TTK/$NEMEROM" --user "$TND:$MK" -T "$TOME/$NEMEROM"; }
tailensf

# Link download 
echo
echo "Link download: $LINKROM"
echo "Link download (sourceforge.net): https://sourceforge.net/projects/$TTK/files/$NEMEROM"

closechat "Tạo rom thành công <br/><br/>Link Download: $LINKROM"
addlabel "Hoàn thành"

else
closechat "Tạo rom thất bại, Xem log: 📱[Actions runs](https://github.com/chamchamfy/RROM/actions/runs/$GITHUB_RUN_ID)"
addlabel "Thất bại"
fi

removelabel "Build"
removelabel "Wait"
