#!/bin/sh
#
# To create a new language pack XX
# > mkdir -p ./i18n/XX/LC_MESSAGES/
# > msginit --input=./i18n/glances.pot --output=./i18n/XX/LC_MESSAGES/glances.po
# Translate using the ./i18n/XX/LC_MESSAGES/glances.po file
# Then add XX to the LANG_LIST
# Run this script
#

LANG_LIST='es fr it pt_BR'

xgettext --language=Python --keyword=_ --output=./i18n/glances.pot ./glances/glances.py

for i in $LANG_LIST; do
   echo "Generate language pack for: $i"
   msgmerge --update --no-fuzzy-matching --backup=off ./i18n/$i/LC_MESSAGES/glances.po ./i18n/glances.pot
   msgfmt ./i18n/$i/LC_MESSAGES/glances.po --output-file ./i18n/$i/LC_MESSAGES/glances.mo
done
