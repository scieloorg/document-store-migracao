#!/bin/bash
set -e

PROCESSING_YEAR=$1
PID_FILE=$2
OUTPUT_DIR=$3

#############
#
# Functions
#
############

# Defines a timestamp function
get_timestamp() {
    date +"%s"
}

# Return the time
get_time() {
    date +"%Y-%m-%d %T"
}

# Format the time in a good way
formated_time() {
    echo "[$(get_time)] -"
}

# Extract articles from article meta
extract_articles() {
    local pids=$1
    ds_migracao --loglevel DEBUG extract "$pids" >"$LOG_FOLDER_PATH/extract.log"
}

# Update mixed citation
update_souce_files_with_mixed_citations() {
    ds_migracao --loglevel DEBUG mixed-citations update \
        "$SOURCE_PATH" >"$LOG_FOLDER_PATH/mixedcitations.log"
}

# Convert articles \0/
convert_articles() {
    ds_migracao --loglevel DEBUG convert >"$LOG_FOLDER_PATH/convert.log"
}

# Pack articles
pack_articles() {
    ds_migracao --loglevel DEBBUG pack >"$LOG_FOLDER_PATH/pack.log"
}

if [ "$#" -ne 3 ]; then
    echo "$(formated_time) Wrong number of parameters."
    echo "$(formated_time) This program requires 3 parameters: 1) year 2) pids 3) file and output dir."
    echo "$(formated_time) Example: ./migrate 2014 br_html_2014_pids.txt /root/html."
    exit 1
fi

#############
#
# Setup variables and folders block
#
############

# Now we could organize our processing inside a folder by year
OUTPUT_ROOT_DIR="$OUTPUT_DIR/$PROCESSING_YEAR"

# Defines enviroment variables to the document-store-migracao
export SOURCE_PATH="$OUTPUT_ROOT_DIR/source"
export CONVERSION_PATH="$OUTPUT_ROOT_DIR/conversion"
export SPS_PKG_PATH="$OUTPUT_ROOT_DIR/packaged"
export INCOMPLETE_SPS_PKG_PATH="$SPS_PKG_PATH"
export CACHE_PATH="$OUTPUT_ROOT_DIR/cache"
export VALID_XML_PATH="$CONVERSION_PATH"
LOG_FOLDER_PATH="$OUTPUT_ROOT_DIR/logs"

# Some platforms could crash if this was not defined
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Creating necessary document-store-migracao folders
echo "$(formated_time) Creating work folders in $OUTPUT_ROOT_DIR."

mkdir -p "$SOURCE_PATH" && mkdir -p "$CONVERSION_PATH" &&
    mkdir -p "$SPS_PKG_PATH" && mkdir -p "$INCOMPLETE_SPS_PKG_PATH" \
    mkdir -p "$CACHE_PATH" && mkdir -p "$LOG_FOLDER_PATH"

#############
#
# Questions
#
############

###
# Cache files question
read -r -e -p "$(formated_time) Do you wanna remove extraction cache file? (y/N)" IGNORE_CAHE_ANSWER
IGNORE_CAHE_ANSWER=${IGNORE_CAHE_ANSWER:-0}

###
# Extract articles question
read -r -e -p "$(formated_time) Do you wanna extract articles? (y/N)" EXTRACT_ARTICLES_ANSWER
EXTRACT_ARTICLES_ANSWER=${EXTRACT_ARTICLES_ANSWER:-0}

###
# Update mixed citation question
read -r -e -p "$(formated_time) Do you wanna update mixed citations? (y/N)" UPDATE_MIXED_CITATION_ANSWER
UPDATE_MIXED_CITATION_ANSWER=${UPDATE_MIXED_CITATION_ANSWER:-0}

###
# Convert articles question
read -r -e -p "$(formated_time) Do you wanna convert articles? (y/N)" CONVERT_ARTICLES_ANSWER
CONVERT_ARTICLES_ANSWER=${CONVERT_ARTICLES_ANSWER:-0}

###
# Pack articles question
read -r -e -p "$(formated_time) Do you wanna pack articles? (y/N)" PACK_ARTICLES_ANSWER
PACK_ARTICLES_ANSWER=${PACK_ARTICLES_ANSWER:-0}

#############
#
# Migration STEPS
#
############

###
# Cache files block
if [ "$IGNORE_CAHE_ANSWER" != "${IGNORE_CAHE_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Removing cache files."
    rm -rf "$CACHE_PATH" && mkdir -p "$CACHE_PATH"
else
    echo "$(formated_time) Keeping cache files."
fi

###
# Extraction block
if [ "$EXTRACT_ARTICLES_ANSWER" != "${EXTRACT_ARTICLES_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the EXTRACT process for $PROCESSING_YEAR with output in $SOURCE_PATH."
    extract_articles "$PID_FILE"
    echo "$(formated_time) Finishing extraction process."
else
    echo "$(formated_time) Ignoring extraction."
fi

###
# Mixed citation update block
if [ "$UPDATE_MIXED_CITATION_ANSWER" != "${UPDATE_MIXED_CITATION_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the mixed citation update in $SOURCE_PATH. It may take some time."
    update_souce_files_with_mixed_citations
    echo "$(formated_time) Finishing mixed citation updates."
else
    echo "$(formated_time) Ignoring mixed citation updates."
fi

###
# Convert articles block
if [ "$CONVERT_ARTICLES_ANSWER" != "${CONVERT_ARTICLES_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the convertion process with output in $CONVERSION_PATH, be patient."
    convert_articles
    echo "$(formated_time) Finishing convertion process."
else
    echo "$(formated_time) Ignoring convertion process."
fi

###
# Convert articles block
if [ "$PACK_ARTICLES_ANSWER" != "${PACK_ARTICLES_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the pack process with output in $SPS_PKG_PATH, it may take a while."
    pack_articles
    echo "$(formated_time) Finishing packing process."
else
    echo "$(formated_time) Ignoring packing process."
fi
