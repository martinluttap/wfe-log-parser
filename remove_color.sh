#!/bin/bash

LOG=$1

if [ $# != 1 ]; then
	echo "Usage: $0 <LOG_PATH>"
	exit 1
fi

sed -r "s/\x1B\[([0-9]{1,3}(;[0-9]{1,2};?)?)?[mGK]//g" -i $LOG
