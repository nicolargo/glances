#!/bin/bash

### Generating Spanish Locale

echo "Para instalar correctamente la traducción española,\n"
echo "debe ejecutar este script como root o con sudo.\n"
echo "\n\n"

echo "Traducción de JeanBoB <jeanbob@jeanbob.eu>\n\n"


echo "Generación del idioma española...\n"
msgfmt i18n/es/LC_MESSAGES/glances.po -o i18n/es/LC_MESSAGES/glances.mo
echo "Instalación en el siguiente directorio: /usr/share/locale/es/LC_MESSAGES/\n"
cp i18n/es/LC_MESSAGES/glances.mo /usr/share/locale/es/LC_MESSAGES/glances.mo
echo "¡Instalación terminado!\n\n"