#!/bin/sh

if [ $(id -u) -ne 0 ]; then
    echo -e "* ERROR: User $(whoami) is not root, and does not have sudo privileges"
    exit 1
fi

if [ ! -f "setup.py" ]; then
    echo -e "* ERROR: Setup file doesn't exist"
    exit 1
fi



python setup.py install --record install.record

for i in $(cat install.record); do
    rm  $i
done

echo -e "\n\n* SUCCESS: Uninstall complete."
rm install.record
