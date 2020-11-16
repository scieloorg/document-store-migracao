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

# Returns a list of folder that articles import step failed
get_import_errors() {
    IMPORT_LOG=$1
    grep ERROR <"$IMPORT_LOG" | grep "Could not import package" | cut -d "'" -f2
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

##
# Reports the size of packaged folder in bytes
report_total_data_size_in_bytes() {
    OUTPUT_FILE_ARG=${1:-""}

    if [ ! -d "$SPS_PKG_PATH" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate data size, there is no folder '$SPS_PKG_PATH'${NC}."
    elif [ -z "$OUTPUT_FILE_ARG" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate data size, there is no output file.${NC}"
    else
        _command=$(du -s "$SPS_PKG_PATH" | awk -F " " '{print $1}')
        echo "TOTAL_BYTES=$_command" >>"$OUTPUT_FILE_ARG"
        echo -e "$(formated_time) ${GREEN}[Report] - Total of bytes.${NC}"
    fi
}

##
# Reports the quantity of failures during import
report_articles_failures_in_import() {
    OUTPUT_FILE_ARG=${1:-""}
    LOG_FILE_PATH_ARG=${2:-"$LOG_FOLDER_PATH/import.log"}

    if [ -z "$OUTPUT_FILE_ARG" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate failures at import, please inform a output file.${NC}"
    elif [ ! -f "$LOG_FILE_PATH_ARG" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate failures at import, there is no ${LOG_FILE_PATH_ARG} log file.${NC}"
    else
        QTY_ARTICLES_FAILED_AT_IMPORT=$(get_import_errors "$LOG_FILE_PATH_ARG" | wc -l | tr -d " ")
        echo "FAILED_TO_IMPORT=$QTY_ARTICLES_FAILED_AT_IMPORT" >>"$OUTPUT_FILE_ARG"
        echo -e "$(formated_time) ${GREEN}[Report] - Articles failures in import.${NC}"
    fi
}

##
# Reports the quantity of failures during conversion
report_articles_failures_in_conversion() {
    OUTPUT_FILE_ARG=${1:-""}
    LOG_FILE_PATH_ARG=${2:-"$LOG_FOLDER_PATH/convert.log"}

    if [ -z "$OUTPUT_FILE_ARG" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate failures at conversion, there is no output file.${NC}"
    elif [ ! -f "$LOG_FILE_PATH_ARG" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate failures at conversion, there is no ${LOG_FILE_PATH_ARG} log file.${NC}"
    else
        QTY_ARTICLES_FAILED_AT_CONVERSION=$(grep "ERROR" <"$LOG_FILE_PATH_ARG" | grep -ic "could not convert file" | tr -d " ")
        echo "FAILED_TO_CONVERT=$QTY_ARTICLES_FAILED_AT_CONVERSION" >>"$OUTPUT_FILE_ARG"
        echo -e "$(formated_time) ${GREEN}[Report] - Articles failures in conversion.${NC}"
    fi
}

##
# Reports the quantity of failures during packing
report_articles_failures_in_pack() {
    OUTPUT_FILE_ARG=${1:-""}

    if [ ! -f "$REPORT_FOLDER_PATH/convertion-to-pack.diff" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to calculate packing errors. There is no convertion-to-pack.diff${NC}"
    else
        QTY_ARTICLES_FAILED_AT_PACK=$(grep -c "<" <"$REPORT_FOLDER_PATH/convertion-to-pack.diff" | tr -d " ")
        echo "FAILED_TO_PACK=$QTY_ARTICLES_FAILED_AT_PACK" >>"$OUTPUT_FILE_ARG"
        echo -e "$(formated_time) ${GREEN}[Report] - Articles failures in pack.${NC}"
    fi
}

##
# Reports the quantity of failures during packing
report_total_of_mixed_citations() {
    OUTPUT_FILE_ARG=${1:-""}
    LOG_FILE="$LOG_FOLDER_PATH/mixedcitations.log"

    if [ ! -f "$LOG_FILE" ]; then
        echo -e "$(formated_time) ${RED}[Report] - Skipping to mixed citations updates. There is no ${LOG_FILE} log file.${NC}"
    else
        QTY_MIXED_CITATION_UPDATED=$(grep -vic "Could not update file" <"$LOG_FILE" | tr -d " ")
        echo "MIXED_CITATION_UPDATED=$QTY_MIXED_CITATION_UPDATED" >>"$OUTPUT_FILE_ARG"
        echo -e "$(formated_time) ${GREEN}[Report] - Mixed citation updates.${NC}"
    fi
}

##
# Reports total of failures
report_total_articles_failures() {
    OUTPUT_FILE_ARG=${1:-""}
    QTY_ARTICLES_FAILED_AT_CONVERSION=${QTY_ARTICLES_FAILED_AT_CONVERSION:-0}
    QTY_ARTICLES_FAILED_AT_IMPORT=${QTY_ARTICLES_FAILED_AT_IMPORT:-0}
    QTY_ARTICLES_FAILED_AT_PACK=${QTY_ARTICLES_FAILED_AT_PACK:-0}

    if [ -z "$OUTPUT_FILE_ARG" ]; then
        echo -e "$(formated_time) ${RED}Skipping to summaryze the total of failures, please inform the output file.${NC}"
        exit 0
    fi

    TOTAL_OF_FAILURES=$((QTY_ARTICLES_FAILED_AT_CONVERSION + QTY_ARTICLES_FAILED_AT_IMPORT + QTY_ARTICLES_FAILED_AT_PACK))
    echo "TOTAL_OF_FAILURES=${TOTAL_OF_FAILURES}" >>"$OUTPUT_FILE_ARG"
    echo -e "$(formated_time) ${GREEN}[Report] - Total articles failures.${NC}"
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
REPORT_FILE="$REPORT_FOLDER_PATH/report.txt"

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

#############
#
# Reports
#
############

echo -e "$(formated_time)${YELLOW} Generating a diff file from PIDs in $SOURCE_PATH and $CONVERSION_PATH with output in $REPORT_FOLDER_PATH.${NC}"
get_diff_pids_from_extract_and_convert_steps

echo -e "$(formated_time)${YELLOW} Generating a diff file from PIDs in $CONVERSION_PATH and $SPS_PKG_PATH with output in $REPORT_FOLDER_PATH.${NC}"
get_diff_pids_from_convert_and_pack_steps

if [ -f "${REPORT_FILE}" ]; then
    echo -e "$(formated_time) Removing previous report file in '${LIGHTGRAY}${REPORT_FILE}${NC}'."
    rm "${REPORT_FILE}" || true
fi

report_total_data_size_in_bytes "${REPORT_FILE}"
report_articles_failures_in_conversion "${REPORT_FILE}"
report_articles_failures_in_import "${REPORT_FILE}"
report_articles_failures_in_pack "${REPORT_FILE}"
report_total_articles_failures "${REPORT_FILE}"
report_total_of_mixed_citations "${REPORT_FILE}"
