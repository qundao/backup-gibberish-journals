#!/usr/bin/env bash
set -eu
shopt -s nullglob

option="$1"
pdf_count="${2:-100}"

update=$(date +%Y-%m-%d )
echo "Process $option, update = $update, pdf = $pdf_count"

echo "run $option"
##################################################
case $option in
"shit")
    python download-shit.py --config shit/config --pdf shit/pdf --limit 50 --pdf-limit "$pdf_count"
    ;;

"rubbish")
    python download-rubbish.py --config rubbish/config.json --pdf rubbish/pdf --pdf-limit "$pdf_count"
    ;;

"joker")
    python download-joker.py --config joker/config.json --pdf joker/pdf --pdf-limit "$pdf_count"
    ;;

"shift")
    python download-shift.py --config shift/config.json --pdf shift/pdf --pdf-limit "$pdf_count"
    ;;

*)
    echo "Unknown case."
    ;;

esac
##################################################

pdf_count=$(find "$option" -name "*.pdf" | wc -l | xargs)
echo "pdf in $option = $pdf_count"


case "$(uname -s)" in
Darwin*)
    echo 'macOS'
    sed -i "" -E "s/(Update at:).*/\1 $update/" README.md
    sed -i "" -E "s/($option.*papers:).*/\1 $pdf_count/" README.md
    ;;

Linux*)
    echo 'Linux'
    sed -i -E "s/(Update at:).*/\1 $update/" README.md
    sed -i -E "s/($option.*papers:).*/\1 $pdf_count/" README.md

    ;;
*)
    echo 'Other OS'
    ;;
esac

echo "Done"
