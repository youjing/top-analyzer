#!/bin/bash

DIR=$(dirname "$(realpath "$0")")
COLUMNS=3000  top -b -n 1 -c -e k -o -PID > ${DIR}/snapshots/top_$(date +%Y%m%d_%H%M).txt
