#!/bin/bash

if [[ -n "$1" ]]
then
	while read line;
		do
			python3 buondua-tui.py $line
		done < $1
else
	echo "Please use a text file to start it."
fi
