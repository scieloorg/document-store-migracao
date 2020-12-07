import argparse
import os
import shutil


NOT_CONVERTED = []
NOT_PACKED = []


def reports_for(year):
    pids_file = f"pids_html/{year}_html.txt"
    year_path = f"html_migracao/{year}"
    logs_path = os.path.join(year_path, "logs")
    reports_path = os.path.join(year_path, "reports")
    source_path = os.path.join(year_path, "source")
    conversion_path = os.path.join(year_path, "conversion")
    packaged_path = os.path.join(year_path, "packaged")

    missing(pids_file, conversion_path, packaged_path)

    pack_log = os.path.join(logs_path, "pack.log")
    packing_files_not_found(pack_log)

    os.system(f"cat {reports_path}/report.txt")


def get_pids(pids_file):
    with open(pids_file, "r") as fp:
        pids = fp.read().splitlines()
    return set([pid for pid in pids if pid])


def get_pids_in_conversion(conversion_path):
    return set(f.split(".")[0]
               for f in os.listdir(conversion_path) if f.endswith(".xml"))


def get_pids_in_packaged(packaged_path):
    return set(f.split("_")[0]
               for f in os.listdir(packaged_path))


def missing(pids_file, conversion_path, packaged_path):
    lista1 = get_pids(pids_file)
    lista2 = get_pids_in_conversion(conversion_path)
    lista3 = get_pids_in_packaged(packaged_path)

    print("HTML")
    print(len(lista1))
    print("")

    print("Convertidos")
    print(len(lista2))
    print("")
    count_items_in_path(conversion_path)
    print("")

    print("Empacotados")
    print(len(lista3))
    print("")

    print("Não convertidos")
    not_converted = lista1 - lista2
    print(len(not_converted))
    for i in sorted(not_converted):
        print(i)
    print("")

    print("Não empacotados")
    not_packaged = lista1 - lista3
    print(len(not_packaged))
    for i in sorted(not_packaged):
        print(i)
    print("")

    NOT_CONVERTED.extend(list(not_converted))
    NOT_PACKED.extend(list(not_packaged))


def packing_files_not_found(pack_log):
    print(pack_log)
    print("pdf missing")
    cmd = f"cat {pack_log}| grep ERROR | grep pid | grep pdf | wc -l"
    os.system(cmd)
    print("")

    print("img missing")
    cmd = f"cat {pack_log}| grep ERROR | grep pid | grep img | wc -l"
    os.system(cmd)
    print("")

    print("erros")
    cmd = f"cat {pack_log}| grep ERROR | wc -l"
    os.system(cmd)
    print("")


def count_items_in_file(file_path):
    cmd = f"wc -l {file_path}"
    os.system(cmd)
    print("")


def count_items_in_path(path):
    print(path)
    cmd = f"ls {path}| wc -l"
    os.system(cmd)
    print("")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("begin", type=int)
    parser.add_argument("end", type=int)
    parser.add_argument("--badfiles", action="store_true")

    args = parser.parse_args()

    y_begin, y_end = args.begin, args.end
    if y_begin > y_end:
        y_begin, y_end = y_end, y_begin
    y_end += 1

    for year in sorted(range(y_begin, y_end), reverse=True):
        print("")
        print("-"*10)
        print(year)
        reports_for(year)

    if args.badfiles:
        with open("pids_html/0000_html.txt", "w") as fp:
            fp.write("\n".join(NOT_CONVERTED))

        for pid in NOT_CONVERTED:
            year = pid[10:14]
            for ext in ("json", "xml"):
                src = f"html_migracao/{year}/source/{pid}.{ext}"
                dst = f"html_migracao/0000/source/{pid}.{ext}"
                shutil.copy(src, dst)


if __name__ == "__main__":
    main()
