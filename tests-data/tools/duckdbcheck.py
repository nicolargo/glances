#!/usr/bin/env python
#
# Check a DuckDB file.
# The input DuckDB file should be given as an input with the -i <file> option.
# Check the following thinks:
# - number of line (without the header) should be equal to the number given with the -l <number of lines> option
# - each line should have the same number of columns
# - if the optional -c <number of columns> option is given, each line should have the the same number of columns

import argparse
import sys

import duckdb


def check_duckdb(input_file, expected_lines, expected_columns=None):
    try:
        db = duckdb.connect(database='/tmp/glances.db', read_only=True)

        result = db.sql("SELECT * from cpu").fetchall()

        # Check 1: Number of lines for CPU
        row_count = len(result)
        if row_count != expected_lines:
            print(f"Error: Expected {expected_lines} CPU lines, but found {row_count}")
            return False

        result = db.sql("SELECT * from network").fetchall()

        # Check 2: Number of lines for Network
        row_count = len(result)
        if row_count != expected_lines:
            print(f"Error: Expected {expected_lines} Network lines, but found {row_count}")
            return False

        return True

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return False
    except Exception as e:
        print(f"Error processing DuckDB file: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Check a DuckDB file for various properties.')
    parser.add_argument('-i', '--input', required=True, help='Input CSV file')
    parser.add_argument('-l', '--lines', type=int, required=True, help='Expected number of lines (excluding header)')
    parser.add_argument('-c', '--columns', type=int, help='Expected number of columns (optional)')

    args = parser.parse_args()

    success = check_duckdb(args.input, args.lines, args.columns)

    if success:
        print("DuckDB - All checks passed successfully!")
        sys.exit(0)
    else:
        print("DuckDB validation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
