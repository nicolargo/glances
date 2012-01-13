#!/bin/bash

### Generating French Locale

echo "Pour réussir l'installation de la localisation française,\n"
echo "vous devez executer ce script sous l'utilisateur root ou avec sudo.\n"
echo "\n\n"

echo "Traduction par JeanBoB <jeanbob@jeanbob.eu>\n\n"


echo "Genération de la langue française...\n"
msgfmt i18n/fr/LC_MESSAGES/glances.po -o i18n/fr/LC_MESSAGES/glances.mo
echo "Installation dans le répertoire /usr/share/locale/fr/LC_MESSAGES/\n"
cp i18n/fr/LC_MESSAGES/glances.mo /usr/share/locale/fr/LC_MESSAGES/glances.mo
echo "Installation terminée\n\n"