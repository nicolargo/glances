#!/bin/bash
set -ev
./unitest-data.py && ./unitest.py && ./unitest-restful.py && ./unitest-xmlrpc.py
