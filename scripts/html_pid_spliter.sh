#!/bin/sh

FILE_PATH=$1
START=$2
END=$3
YEAR_FILE_NAME_SUFIX="_html"

if [ "$#" -ne 3 ]; then
    echo "Please inform arguments in this sequence:"
    echo "1) HTML pids file"
    echo "2) start year"
    echo "3) End year"
fi

if [ ! -d "./output" ]; then
    mkdir output
fi

for i in $(seq $START $END); do
    echo "Ano: "$i
    filename='output/'$i$YEAR_FILE_NAME_SUFIX'.txt'
    awk 'substr($0,11,4) ~ /^'$i'/ {print}' $FILE_PATH >$filename
    echo "Gerado arquivo: "$filename" para ano: "$i
done

