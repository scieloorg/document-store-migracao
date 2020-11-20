# Migration Tool Usage Instruction and Examples

This is the complete utilization guide for this tool, these next sections will explain how this application works and how users can do a complete HTML migration to XML migration to the SciELO Publishing Framework.

## Topics
1. Obtaining HTML documents
2. Converting HTML to XML documents
3. [Updating documents' mixed citations](#3-\--updating-documents-mixed-citations)
4. [Generating documents packages](#4-\--Generating documents packages)
5. Importing documents packages to the Publish Platform
6. Committing the relationship between documents and issues

## 3 - Updating documents' mixed citations

The documents must have their mixed citations updated, its important to preserve the quality of your collection. The information stored in the articles' database or paragraphs' databases is essential to finish this task, then please make sure you have access to these databases.

First, locate the database where articles paragraphs are located, this location can vary according to the strategy adopted by the collection. In the SciELO Brazil this information is in two points, these are:
- [1] Articles master file (`/databases/article/article.mst`)
- [2] Articles paragraphs files (`/database/article/p/**/*.mst`)

### 3.1 - Creating paragraphs cache

For this guide, we will work with the first option [1] then all examples will use this source as the paragraphs database. In your terminal execute the command:

```shell
ds_migracao mixed-citations --help
```

You should see the two commands available (`set-cache` and `update`) and a short usage text. Be free to read the text and back here to continue.

The first command `set-cache` should be executed at least one time before the XML updates. So let us create our paragraphs cache database using it (it may take some time according to the database size).

```shell
ds_migracao mixed-citations set-cache /databases/article/article.mst
```

Wait until the commands finish (it will count as zero until that) and see if paragraphs files were created as expected. Open the folder `xml/paragraphs` and see the files.

### 3.2 - Updating articles' mixed citations

The second command `update` must be executed after `set-cache` command, so execute:
```shell
ds_migracao mixed-citations update xml/conversion
```

It may take some time depending on the quantity of XMLs you are updating. For comparison updating `24.000` articles will take approximately 1 hour.

After the command finishes, you will have articles' mixed-citations updated if everything works as expected.

### 3.3 - Troubleshooting 

It is important to make sure if everything works and if all articles were updated for that you should pay attention to all error logging printed in the terminal or inside the migration log directory.

Look closer to messages like `file not found` or `access denied` during previous commands.

## 4 - Generating documents packages

Documents Packages is the phase in which we create packages with all the necessary adjustments to be stored in a data store.

This phase is also necessary so that the renditions and assets are all available and accessible via the xml file.
 
In order to run the `` packing`` phase, it is necessary to perform some predicted configurations, therefore, it is necessary to add two environment variables `` SOURCE_PDF_FILE`` and `` SOURCE_IMG_FILE``.

By default, these variables have the values:

SOURCE_IMG_FILE = "bases"
SOURCE_PDF_FILE = "htdocs"

You can change these values by creating the following environment variables:

```shell
export SOURCE_IMG_FILE = path
export SOURCE_PDF_FILE = path
```

To run the packing, it is possible with the following command:

```shell
ds_migracao --loglevel DEBUG pack
```

Optionally it is possible to run the pack for only one xml, see:

```shell
ds_migracao --loglevel DEBUG pack -f path
```

Help:

```shell
ds_migracao --loglevel DEBUG pack -help
```
