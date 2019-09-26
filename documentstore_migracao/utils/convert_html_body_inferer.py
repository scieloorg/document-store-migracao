
from documentstore_migracao import config
from documentstore_migracao.utils import files


PREFIX_AND_TAG_ITEMS = (
    tuple(item.strip().split("|"))
    for item in open(config.CONVERSION_TAGS).readlines()
)
LEN_AND_PREFIX_AND_TAG_ITEMS = sorted(
    [
        (len(prefix), prefix, tag)
        for prefix, tag in PREFIX_AND_TAG_ITEMS
    ],
    reverse=True)


INFERER_PREFIX_AND_TAG_ITEMS = tuple(
    (prefix, tag)
    for _len, prefix, tag in LEN_AND_PREFIX_AND_TAG_ITEMS
)

INFERER_ITEMS_BY_PREFIX = {}
INFERER_ITEMS_BY_TAG = {}
for prefix, tag in INFERER_PREFIX_AND_TAG_ITEMS:
    k = prefix[0]
    INFERER_ITEMS_BY_PREFIX[k] = INFERER_ITEMS_BY_PREFIX.get(k, [])
    INFERER_ITEMS_BY_PREFIX[k].append((prefix, tag))
    INFERER_ITEMS_BY_TAG[tag] = INFERER_ITEMS_BY_TAG.get(tag, [])
    INFERER_ITEMS_BY_TAG[tag].append((prefix, tag))

for k, v in INFERER_ITEMS_BY_PREFIX.items():
    INFERER_ITEMS_BY_PREFIX[k] = sorted(v, reverse=True)


class Inferer:

    REFTYPE = {"table-wrap": "table", "ref": "bibr"}
    BODY_SECS = (
        "intr",
        "subj",
        "meto",
        "méto",
        "disc",
        "bibr",
        "resu",
        "abst",
        "mate",
        "refe",
        "ackn",
        "text",
    )

    def ref_type(self, elem_name):
        return self.REFTYPE.get(elem_name, elem_name)

    def tag_and_reftype_from_name(self, name):
        if not name:
            return
        k = name[0]
        if k.isalpha():
            for prefix, tag in INFERER_ITEMS_BY_PREFIX.get(k, []):
                if name.startswith(prefix):
                    if len(prefix) == 1 and not name[len(prefix):].isdigit():
                        return "fn", "fn"
                    return tag, self.ref_type(tag)
            for prefix, tag in INFERER_PREFIX_AND_TAG_ITEMS:
                if len(prefix) > 1:
                    if prefix in name:
                        return tag, self.ref_type(tag)
        if not k.isalnum():
            return "symbol", "fn"
        return "fn", "fn"

    def tag_and_reftype_from_a_href_text(self, a_href_text):
        if not (a_href_text or "").strip():
            return
        a_href_text = a_href_text.strip().lower()
        for i, c in enumerate(a_href_text):
            if c.isalnum():
                break
        text = a_href_text[i:]
        k = text[0]
        for prefix, tag in INFERER_ITEMS_BY_PREFIX.get(k, []):
            if text.startswith(prefix) and len(prefix) > 1:
                return tag, self.ref_type(tag)
        if a_href_text[0].isalpha():
            if len(a_href_text) == 1:
                return "fn", "fn"
            if a_href_text[:4] in self.BODY_SECS:
                return "target", "other"
            if "corresp" in text or "address" in text or "endereço" in text:
                return "corresp", "corresp"
            if "image" in text:
                return "fig", "fig"
            if "annex" in text:
                return "app", "app"
            return "undefined", "undefined"
        return "fn", "fn"

    def tag_and_reftype_and_id_from_filepath(self, file_path, elem_name=None):
        filename, __ = files.extract_filename_ext_by_path(file_path)
        if elem_name:
            prefix_and_tag_items = INFERER_ITEMS_BY_TAG.get(elem_name, [])
            prefix_and_tag_items.append((elem_name[0], elem_name))
        else:
            prefix_and_tag_items = INFERER_PREFIX_AND_TAG_ITEMS
        for prefix, tag in prefix_and_tag_items:
            if prefix == filename:
                return tag, self.ref_type(tag), filename
            if prefix in filename:
                parts = filename.split(prefix)
                if len(parts) < 2:
                    continue
                if parts[0] and parts[0][-1].isalpha():
                    continue
                if parts[1] and parts[1][0].isalpha():
                    continue
                if parts[1]:
                    return tag, self.ref_type(tag), prefix + "".join(parts[1:])
