#!/bin/bash

echo "Positional Parameters"
echo '$0 = ' $0
echo '$1 = ' $1
echo '$2 = ' $2
if [ "$3" != "" ]; then
	echo '$3 = ' $3
fi
