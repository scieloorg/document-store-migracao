def read(filepath):
    return [item.strip() for item in open(filepath).readlines()]


def write(filepath, content):
    with open(filepath, "w") as fp:
        fp.write(content)


def select(items):
    return [item 
            for item in items
            if "00010" in item and item[-1] in ["1", "4"]]



items = read("/Users/robertatakenaka/Downloads/html_pids.txt")
items = select(items)
write("/Users/robertatakenaka/Downloads/selecao_br.txt", "\n".join(items))


items = read("/Users/robertatakenaka/Downloads/html_pids_spa.txt")
items = select(items)
write("/Users/robertatakenaka/Downloads/selecao_spa.txt", "\n".join(items))
