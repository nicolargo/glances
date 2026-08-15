#!/usr/bin/env python
#
# Check a CSV file.
# The input CSV file should be given as an input with the -i <file> option.
# Check the following thinks:
# - number of line (without the header) should be equal to the number given with the -l <number of lines> option
# - each line should have the same number of columns
# - if the optional -c <number of columns> option is given, each line should have the the same number of columns

import argparse
import csv
import sys


def check_csv(input_file, expected_lines, expected_columns=None):
    try:
        with open(input_file, newline='') as csvfile:
            reader = csv.reader(csvfile)

            # Read header
            header = next(reader, None)
            if header is None:
                print("Error: CSV file is empty")
                return False

            header_columns = len(header)
            print(f"Header has {header_columns} columns")

            # Read all the data rows
            rows = list(reader)
            row_count = len(rows)

            # Check 1: Number of lines
            if row_count != expected_lines:
                print(f"Error: Expected {expected_lines} lines, but found {row_count}")
                return False
            print(f"Line count check passed: {row_count} lines (excluding header)")

            # Check 2: Consistent number of columns
            column_counts = [len(row) for row in rows]
            if len(set(column_counts)) > 1:
                print("Error: Not all rows have the same number of columns")
                for i, count in enumerate(column_counts):
                    if count != header_columns:
                        print(f"Row {i + 1} has {count} columns (different from header)")
                return False
            print("Column consistency check passed: All rows have the same number of columns")

            # Check 3: Optional - specific number of columns
            if expected_columns is not None:
                if header_columns != expected_columns:
                    print(f"Error: Expected {expected_columns} columns, but found {header_columns}")
                    return False
                print(f"Column count check passed: {header_columns} columns")

            return True

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return False
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Check a CSV file for various properties.')
    parser.add_argument('-i', '--input', required=True, help='Input CSV file')
    parser.add_argument('-l', '--lines', type=int, required=True, help='Expected number of lines (excluding header)')
    parser.add_argument('-c', '--columns', type=int, help='Expected number of columns (optional)')

    args = parser.parse_args()

    success = check_csv(args.input, args.lines, args.columns)

    if success:
        print("CSV - All checks passed successfully!")
        sys.exit(0)
    else:
        print("CSV validation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
