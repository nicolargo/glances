#!/bin/sh

find ./glances/ -type f -name "*.py" -exec sh -c '
    duplicate_found=0
    for file; do
        last_line=$(tail -n 1 "$file")
        second_last_line=$(tail -n 2 "$file" | head -n 1)
        if [ -n "$last_line" ] && [ -n "$second_last_line" ] && [ "$last_line" = "$second_last_line" ]; then
            echo "Duplicate last line in: $file"
            duplicate_found=1
        fi
    done
    exit $duplicate_found
' sh {} +
