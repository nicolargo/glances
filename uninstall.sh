#!/bin/bash

if [ "$(id -u)" != "0" ]; then
    echo "* ERROR: User $(whoami) is not root, and does not have sudo privileges"
    exit 1
fi

if [ ! -f "setup.py" ]; then
    echo -e "* ERROR: Setup file doesn't exist"
    exit 1
fi



python setup.py install --record install.record

while IFS= read -r i; do
    rm "$i"
done < install.record

echo -e "\n\n* SUCCESS: Uninstall complete."
rm install.record
