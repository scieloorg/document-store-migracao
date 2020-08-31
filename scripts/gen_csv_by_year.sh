#!/bin/sh

START=2002
END=2020
FILE_PATH=$1
YEAR_FILE_NAME_SUFIX="_native_xml"

for i in $(seq $START $END);
do
    echo "Ano: "$i;
    filename=$i$YEAR_FILE_NAME_SUFIX'.csv';
    awk -F ',' '$4 ~ /^ *'$i'/ {print}' $FILE_PATH > $filename;
    echo "Gerado arquivo: "$filename" para ano: "$i
done;
