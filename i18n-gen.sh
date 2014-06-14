#!/bin/bash

#Calculates the direcory of the script in case it is run from another directory
ROOT="${0%%i18n-gen.sh}"

function usage() {
        cat <<EOT
Usage: $0 <subcommand> language_code

Available subcommands:
    init
            creates a new folder for a new language
    update
            updates an existing language file with new Strings from the sources
    gen
            generates the parsed language file

update and gen also accept the wildcard language_code ALL

Suggested Workflows (with XX as language_code):
    New Language
        1. $0 init XX
        2. translation of ${ROOT}i18n/XX/LC_MESSAGES/glances.po
        3. $0 gen XX
    Update Language
        1. $0 update XX
        2. update translations of ${ROOT}i18n/XX/LC_MESSAGES/glances.po
        3. $0 gen XX
EOT
exit
}

function gen_pot() {
	xgettext --language=Python --keyword=_ --output=${ROOT}i18n/glances.pot `find ${ROOT}glances/ -name "*.py"`
}

OPERATION="$1"
shift

if [ -z "$1" ]; then
	usage
fi

case "$OPERATION" in
	init)
		# If there is already a language file for specified language there is no need to generate a new one
		# doing so would result in a loss of all already translated strings for that language
		if [ -f "${ROOT}i18n/$1/LC_MESSAGES/glances.po" ]; then
			echo "Error:"
			echo "Language file for language $1 already exists"
			echo "Please run \"$0 help\" for more information"
			exit 1
		fi
		# Actual generation
		mkdir -p ${ROOT}i18n/$1/LC_MESSAGES/
		gen_pot
		msginit --locale="$1" --input=${ROOT}i18n/glances.pot --output=${ROOT}i18n/$1/LC_MESSAGES/glances.po
		exit 0
		;;
	update)
		# When the language code is ALL fetch all language codes and save them
		# else test if the specified language code really exists
		if [ "$1" = "ALL" ]; then
			LANG_LIST="$(ls -d ${ROOT}i18n/*/ | awk -F / '{print $(NF-1)}')"
		else
			if [ ! -f "${ROOT}i18n/$1/LC_MESSAGES/glances.po" ]; then
				echo "Error:"
				echo "Language file for language $1 doesn't exists"
				echo "Please run \"$0 help\" for more information"
				exit 1
			fi
			LANG_LIST="$1"
		fi
		# regenerate the pot file so that it conatins the new strings and then update the language files accordingly
		gen_pot
		for i in $LANG_LIST; do
			msgmerge --update --no-fuzzy-matching --backup=off ${ROOT}i18n/$i/LC_MESSAGES/glances.po ${ROOT}i18n/glances.pot
			echo "Language file for language $i updated"
		done
		exit 0
		;;
	gen)
		# When the language code is ALL fetch all language codes and save them
		# else test if the specified language code really exists
		if [ "$1" = "ALL" ]; then
			LANG_LIST="$(ls -d ${ROOT}i18n/*/ | awk -F / '{print $(NF-1)}')"
		else
			if [ ! -f "${ROOT}i18n/$1/LC_MESSAGES/glances.po" ]; then
				echo "Error:"
				echo "Language file for language $1 doesn't exists"
				echo "Please run \"$0 help\" for more information"
				exit 1
			fi
			LANG_LIST="$1"
		fi
		# compile the language files 
		for i in $LANG_LIST; do
			msgfmt ${ROOT}i18n/$i/LC_MESSAGES/glances.po --output-file ${ROOT}i18n/$i/LC_MESSAGES/glances.mo
			echo "Compiled language file for language $i generated"
		done
		exit 0
		;;
	*)
		# if anything other is entered as first argument print the usage overview
		# so, the message to run "i18n-gen.sh help" is a LIE but who cares since the cake was a lie in the first place!
		usage
		;;
esac
