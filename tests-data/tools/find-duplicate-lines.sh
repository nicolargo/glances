find ./glances/ -type f -name "*.py" -exec sh -c '
    for file; do
        last_line=$(tail -n 1 "$file")
        second_last_line=$(tail -n 2 "$file" | head -n 1)
        if [ -n "$last_line" ] && [ -n "$second_last_line" ] && [ "$last_line" = "$second_last_line" ]; then
            echo "Duplicate last line in: $file"
        fi
    done
' sh {} +
