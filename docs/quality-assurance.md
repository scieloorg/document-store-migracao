
# Quality Assurance
After migrating the collection you should verify if the process worked as expected. This guide assists you to verify if articles are not available at the new Website.

## Verifying articles' availability at the new Website

Use a list containing the articles identifiers (also known as PID) that you want to check. Also, you need to provide an URL that is used to check if articles are accessible. For example, you can define certain URL templates:

- `http://www.scielo.br/article/\$id`.
- `http://www.scielo.br/scielo.php?script=sci_arttext&pid=\$id`.

The `$id` in the URLs is used to replace identifiers collected in the first step (the backslash is used to escape `$` in Linux terminal).

### Example

We made one list containing five identifiers (aka PIDs), see:

```shell
$ cat articles_identifiers.txt
```
```
S0044-59672004000100001
S0044-59672004000100002
S0044-59672004000100003
S0044-59672004000100004
S0044-59672004000100005
```
So let's check if they are available in the new Website:

```shell
ds_migracao quality articles_identifiers.txt "http://new-website.scielo.br/article/\$id"
``` 

If all is well, no message will be displayed in the terminal. Otherwise, manually check what happened to all articles reported as missing. Be free to explore other options in the tool, execute:

```shell
ds_migracao quality --help
```
