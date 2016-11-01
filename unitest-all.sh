#!/bin/bash
set -ev
./unitest.py && ./unitest-restful.py && ./unitest-xmlrpc.py
