#!/bin/bash
set -e

PROCESSING_YEAR=$1
PID_FILE=$2
OUTPUT_DIR=$3

#############
#
# COLORS
#
############
NC='\033[0m' # No Color
YELLOW='\033[1;33m'
LIGHTGRAY='\033[0,37m'
RED='\033[0;31m'
GREEN='\033[1;32m'

usage="$(basename "$0") [-h --help] - A simple script to help during migration process

where:
    -h --help       show this help text
    year            set the year that will be migrated
    file            set the file containing a list of HTML pids
    folder          set the output folder where migration work files will be placed

Example:
    ./$(basename "$0") 2010 2010_html_pids.txt  /home/scielo/migration

    This command above will setup the migration for the year of 2010
    using the '2010_html_pids.txt' file and will produce the work files
    inside the folder '/home/scielo/migration/2010'."

if [ "$#" = 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$#" -lt 3 ]; then
    echo "$usage"
    exit 0
fi

set -u

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
    ds_migracao --loglevel DEBUG pack >"$LOG_FOLDER_PATH/pack.log"
}

#############
#
# Report functions
#
############

# Generate the difference of pids from extract to convert
get_diff_pids_from_extract_and_convert_steps() {
    SOURCE_TEMP_FILE="/tmp/$(get_timestamp).s"
    TARGET_TEMPFILE="/tmp/$(get_timestamp).t"
    find "$SOURCE_PATH" -name "*.xml" -type f \
        -exec basename {} \; | cut -d "." -f1 | sort -n >"$SOURCE_TEMP_FILE"
    find "$CONVERSION_PATH" -name "*.xml" -type f \
        -exec basename {} \; | cut -d "." -f1 | sort -n >"$TARGET_TEMPFILE"
    diff "$SOURCE_TEMP_FILE" "$TARGET_TEMPFILE" >"$REPORT_FOLDER_PATH/extract-to-convertion.diff" || true

    # Remove temporary files
    rm "$SOURCE_TEMP_FILE" "$TARGET_TEMPFILE"
}

##
# Generating diff from convertion to packing steps
get_diff_pids_from_convert_and_pack_steps() {
    SOURCE_TEMP_FILE="/tmp/$(get_timestamp).s"
    TARGET_TEMPFILE="/tmp/$(get_timestamp).t"

    find "$CONVERSION_PATH" -name "*.xml" -type f \
        -exec basename {} \; | cut -d "." -f1 | sort -n >"$SOURCE_TEMP_FILE"

    # getting all articles' pids
    find "$SPS_PKG_PATH" -name "*.xml" -type f \
        -exec awk -v tgt='scielo-v2' 's=index($0,tgt) {print substr($0, s+11, 23)}' {} \; |
        sort -n >"$TARGET_TEMPFILE"

    # doing the diff
    diff "$SOURCE_TEMP_FILE" "$TARGET_TEMPFILE" >"$REPORT_FOLDER_PATH/convertion-to-pack.diff" || true

    # Remove temporary files
    rm "$SOURCE_TEMP_FILE" "$TARGET_TEMPFILE"
}

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
REPORT_FOLDER_PATH="$OUTPUT_ROOT_DIR/reports"

# Some platforms could crash if this was not defined
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Creating necessary document-store-migracao folders
echo "$(formated_time) Creating work folders in $OUTPUT_ROOT_DIR."

mkdir -p "$SOURCE_PATH" && mkdir -p "$CONVERSION_PATH" &&
    mkdir -p "$SPS_PKG_PATH" && mkdir -p "$INCOMPLETE_SPS_PKG_PATH" \
    mkdir -p "$CACHE_PATH" && mkdir -p "$LOG_FOLDER_PATH" &&
    mkdir -p "$REPORT_FOLDER_PATH"

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

echo -e "$(formated_time)${YELLOW} Generating a diff file from PIDs in $SOURCE_PATH and $CONVERSION_PATH with output in $REPORT_FOLDER_PATH.${NC}"
get_diff_pids_from_extract_and_convert_steps

echo -e "$(formated_time)${YELLOW} Generating a diff file from PIDs in $CONVERSION_PATH and $SPS_PKG_PATH with output in $REPORT_FOLDER_PATH.${NC}"
get_diff_pids_from_convert_and_pack_steps
