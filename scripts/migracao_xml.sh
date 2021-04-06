#!/bin/bash
set -e

PROCESSING_YEAR=$1
PID_FILE=$2
OUTPUT_DIR=$3
ENV_FILE=$4

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
    file            set the file containing a list of XML CSV format file
    folder          set the output folder where migration work files will be placed
    env-file        set the variable enviroment file

Example:
    ./$(basename "$0") 2021 2021-xml.csv  /home/scielo/migration

    This command above will setup the migration for the year of 2021
    using the '2021-xml.csv' file and will produce the work files
    inside the folder '/home/scielo/migration/2021'."

if [ "$#" = 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$#" -lt 4 ]; then
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
package_articles() {
    local xmls=$1
    local imgs=$2
    local pdfs=$3
    local output=$4
    local csv=$5

    ds_migracao --loglevel DEBUG pack_from_site -X "$xmls" \
        -Ifolder "$imgs" \
        -P "$pdfs" \
        -O "$output" \
        -A "$csv" >"$LOG_FOLDER_PATH/pack.log"
}

# Import articles to Kernel and Minio
import_articles() {
    local mongodb_uri="$1"
    local kernel_db="$2"
    local minio_host="$3"
    local minio_access_key="$4"
    local minio_secret_key="$5"
    local pid_database_dsn="$6"
    local packaged_folder="$SPS_PKG_PATH"
    local imported_articles_link_file="$SPS_LINK_FILE"

    if [ ! -z "$XML_IMPORTING_MINIO_IS_SECURE" ]; then
        ds_migracao --loglevel DEBUG import --uri "$mongodb_uri" \
            --db "$kernel_db" \
            --minio_host "$minio_host" \
            --minio_access_key "$minio_access_key" \
            --minio_secret_key "$minio_secret_key" \
            --minio_is_secure \
            --folder "$packaged_folder" \
            --pid_database_dsn "$pid_database_dsn" \
            --output "$imported_articles_link_file" >"$LOG_FOLDER_PATH/import.log"
    else
        ds_migracao --loglevel DEBUG import --uri "$mongodb_uri" \
            --db "$kernel_db" \
            --minio_host "$minio_host" \
            --minio_access_key "$minio_access_key" \
            --minio_secret_key "$minio_secret_key" \
            --folder "$packaged_folder" \
            --pid_database_dsn "$pid_database_dsn" \
            --output "$imported_articles_link_file" >"$LOG_FOLDER_PATH/import.log"
    fi
}

# Validating the enviroment file

if [ ! -e "$ENV_FILE" ]; then
    echo -e "$(formated_time) ${RED}The '$ENV_FILE' variable file does not exist, please create it.${NC}"
    exit 1
fi

echo -e "$(formated_time) ${GREEN}Reading the '${ENV_FILE}' variable file and configuring the script.${NC}"

#############
#
# Setup variables and folders block
#
############

# Now we could organize our processing inside a folder by year
OUTPUT_ROOT_DIR="$OUTPUT_DIR/$PROCESSING_YEAR"

# Defines variables to the document-store-migracao
LOG_FOLDER_PATH="$OUTPUT_ROOT_DIR/logs"
REPORT_FOLDER_PATH="$OUTPUT_ROOT_DIR/reports"
SPS_PKG_PATH="$OUTPUT_ROOT_DIR/packaged"
SPS_LINK_FILE_DIR="$OUTPUT_ROOT_DIR/link"
SPS_LINK_FILE="$SPS_LINK_FILE_DIR/link.jsonl"

# Some platforms could crash if this was not defined
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

eval $(egrep -v '^#' $ENV_FILE | xargs)

XML_MIGRATION_XML_SOURCE_FOLDER=${XML_MIGRATION_XML_SOURCE_FOLDER:-""}
XML_MIGRATION_IMG_SOURCE_FOLDER=${XML_MIGRATION_IMG_SOURCE_FOLDER:-""}
XML_MIGRATION_PDF_SOURCE_FOLDER=${XML_MIGRATION_PDF_SOURCE_FOLDER:-""}
XML_MIGRATION_ISSN_JOURNALS_FILE=${XML_MIGRATION_ISSN_JOURNALS_FILE:-""}

# Importing variables
XML_IMPORTING_MONGODB_URI=${XML_IMPORTING_MONGODB_URI:-""}
XML_IMPORTING_PID_DATABASE_DSN=${XML_IMPORTING_PID_DATABASE_DSN:-""}
XML_IMPORTING_KERNEL_DABATASE=${XML_IMPORTING_KERNEL_DABATASE:-""}

XML_IMPORTING_MINIO_HOST=${XML_IMPORTING_MINIO_HOST:-""}
XML_IMPORTING_MINIO_ACCESS_KEY=${XML_IMPORTING_MINIO_ACCESS_KEY:-""}
XML_IMPORTING_MINIO_SECRET_KEY=${XML_IMPORTING_MINIO_SECRET_KEY:-""}
XML_IMPORTING_MINIO_IS_SECURE=${XML_IMPORTING_MINIO_IS_SECURE:-""}

declare -a CONFIGURED_VARIABLES=(
    XML_MIGRATION_XML_SOURCE_FOLDER
    XML_MIGRATION_IMG_SOURCE_FOLDER
    XML_MIGRATION_PDF_SOURCE_FOLDER
    XML_MIGRATION_ISSN_JOURNALS_FILE
    XML_IMPORTING_MONGODB_URI
    XML_IMPORTING_PID_DATABASE_DSN
    XML_IMPORTING_KERNEL_DABATASE
    XML_IMPORTING_MINIO_HOST
    XML_IMPORTING_MINIO_ACCESS_KEY
    XML_IMPORTING_MINIO_SECRET_KEY)

# Verify configuration variables
for variable in "${CONFIGURED_VARIABLES[@]}"; do
    if [ -z "${!variable}" ]; then
        echo -e "$(formated_time) ${YELLOW}Please configure the $variable in the '${ENV_FILE}'.${NC}"
        exit 1
    fi
done

# Substitute the minio secure argument
# if [ ! -z "$XML_IMPORTING_MINIO_IS_SECURE" ]; then
#     XML_IMPORTING_MINIO_IS_SECURE="true"
# else
#     XML_IMPORTING_MINIO_IS_SECURE="false"
# fi

echo $XML_IMPORTING_MINIO_IS_SECURE

# Creating necessary document-store-migracao folders
echo "$(formated_time) Creating work folders in $OUTPUT_ROOT_DIR."

mkdir -p "$OUTPUT_ROOT_DIR" && mkdir -p "$LOG_FOLDER_PATH" &&
    mkdir -p "$REPORT_FOLDER_PATH" && mkdir -p "$SPS_PKG_PATH" &&
    mkdir -p "$SPS_LINK_FILE_DIR"

# Check the utility application

if ! command -v ds_migracao &>/dev/null; then
    echo -e "$(formated_time) ${RED}The 'ds_migracao' programm is not available in your command line, please verify.${NC}"
    exit
fi

#############
#
# Questions
#
############

###
# Pack articles question
read -r -e -p "$(formated_time) Do you wanna pack the XML files? (y/N)" PACK_XML_ARTICLES_ANSWER
PACK_XML_ARTICLES_ANSWER=${PACK_XML_ARTICLES_ANSWER:-0}

###
# Import articles question
read -r -e -p "$(formated_time) Do you wanna import the previous packaged articles? (y/N)" IMPORT_ARTICLES_ANSWER
IMPORT_ARTICLES_ANSWER=${IMPORT_ARTICLES_ANSWER:-0}

###
# Package block
if [ "$PACK_XML_ARTICLES_ANSWER" != "${PACK_XML_ARTICLES_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the Packing process for $PROCESSING_YEAR with output in $SPS_PKG_PATH."
    package_articles "$XML_MIGRATION_XML_SOURCE_FOLDER" \
        "$XML_MIGRATION_IMG_SOURCE_FOLDER" \
        "$XML_MIGRATION_PDF_SOURCE_FOLDER" \
        "$SPS_PKG_PATH" \
        "$PID_FILE"
    echo "$(formated_time) Finishing xml packing process."
else
    echo "$(formated_time) Ignoring xml packing process."
fi

###
# Importing block
if [ "$IMPORT_ARTICLES_ANSWER" != "${IMPORT_ARTICLES_ANSWER#[Yy]}" ]; then
    echo "$(formated_time) Starting the importing process for $PROCESSING_YEAR with output in $SPS_LINK_FILE."
    import_articles "$XML_IMPORTING_MONGODB_URI" \
        "$XML_IMPORTING_KERNEL_DABATASE" \
        "$XML_IMPORTING_MINIO_HOST" \
        "$XML_IMPORTING_MINIO_ACCESS_KEY" \
        "$XML_IMPORTING_MINIO_SECRET_KEY" \
        "$XML_IMPORTING_PID_DATABASE_DSN"
    echo "$(formated_time) Finishing importing process."
else
    echo "$(formated_time) Ignoring importing process."
fi
