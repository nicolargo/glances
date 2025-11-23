#!/bin/sh

make clean
make html
LC_ALL=C make man
