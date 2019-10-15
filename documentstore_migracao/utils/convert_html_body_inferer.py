import json
import os

from documentstore_migracao import config
from documentstore_migracao.utils import files


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

    def __init__(self):
        self.rules = InfererRules(config.INFERERER_RULES_FILE_PATH)

    def ref_type(self, elem_name):
        return self.REFTYPE.get(elem_name, elem_name)

    def tag_and_reftype_from_name(self, name):
        if not name:
            return
        k = name[0]
        if k.isalpha():
            for clue, tag in self.rules.sorted_by_clue_first_char.get(k, []):
                if name.startswith(clue):
                    if len(clue) == 1 and not name[len(clue) :].isdigit():
                        return "fn", "fn"
                    return tag, self.ref_type(tag)
            for clue, tag in self.rules.sorted_clue_and_tags_items:
                if len(clue) > 1:
                    if clue in name:
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
        for clue, tag in self.rules.sorted_by_clue_first_char.get(k, []):
            if text.startswith(clue) and len(clue) > 1:
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
            clue_and_tag_items = self.rules.sorted_by_tag.get(elem_name, [])
            clue_and_tag_items.append((elem_name[0], elem_name))
        else:
            clue_and_tag_items = self.rules.sorted_clue_and_tags_items
        for clue, tag in clue_and_tag_items:
            if clue == filename:
                return tag, self.ref_type(tag), filename
            if clue in filename:
                parts = filename.split(clue)
                if len(parts) < 2:
                    continue
                if parts[0] and parts[0][-1].isalpha():
                    continue
                if parts[1] and parts[1][0].isalpha():
                    continue
                if parts[1]:
                    return tag, self.ref_type(tag), clue + "".join(parts[1:])


class InfererRules:
    def __init__(self, rules_file_path):
        self.rules_file_path = rules_file_path
        file_path, ext = os.path.splitext(rules_file_path)
        dirname = os.path.dirname(rules_file_path)
        self.json_sorted_by_clue_first_char = os.path.join(
            dirname, "_inferer_clue.json"
        )
        self.json_sorted_by_tag = os.path.join(dirname, "_inferer_tags.json")
        self._unsorted_clue_and_tag_items = None
        self._sorted_clue_and_tags_items = None
        self._sorted_by_clue_len_in_reverse_order = None
        self._sorted_by_tag = None
        self._sorted_by_clue_first_char = None

    @property
    def unsorted_clue_and_tag_items(self):
        if not self._unsorted_clue_and_tag_items:
            with open(self.rules_file_path, "r") as fp:
                self._unsorted_clue_and_tag_items = (
                    tuple(item.strip().split("|")) for item in fp.readlines()
                )
        return self._unsorted_clue_and_tag_items

    @property
    def sorted_by_clue_len_in_reverse_order(self):
        if not self._sorted_by_clue_len_in_reverse_order:
            self._sorted_by_clue_len_in_reverse_order = sorted(
                [
                    (len(text), text, tag)
                    for text, tag in self.unsorted_clue_and_tag_items
                ],
                reverse=True,
            )
        return self._sorted_by_clue_len_in_reverse_order

    @property
    def sorted_clue_and_tags_items(self):
        if not self._sorted_clue_and_tags_items:
            self._sorted_clue_and_tags_items = [
                (text, tag)
                for lent, text, tag in self.sorted_by_clue_len_in_reverse_order
            ]
        return self._sorted_clue_and_tags_items

    def classify_items_by_tag(self):
        d = {}
        for clue_len, clue, tag in self.sorted_by_clue_len_in_reverse_order:
            d[tag] = d.get(tag, [])
            d[tag].append((clue, tag))
        return d

    def classify_items_by_clue_first_char(self):
        d = {}
        for clue_len, clue, tag in self.sorted_by_clue_len_in_reverse_order:
            first_char = clue[0]
            d[first_char] = d.get(first_char, [])
            d[first_char].append((clue, tag))
        return d

    def get_data(self, json_file_path, classification_function):
        data = None
        if os.path.isfile(json_file_path):
            with open(json_file_path, "r") as fp:
                data = json.loads(fp.read())
        if not data:
            data = classification_function()
            if data:
                with open(json_file_path, "w") as fp:
                    fp.write(json.dumps(data))
        return data

    @property
    def sorted_by_tag(self):
        if not self._sorted_by_tag:
            self._sorted_by_tag = self.get_data(
                self.json_sorted_by_tag, self.classify_items_by_tag
            )
        return self._sorted_by_tag

    @property
    def sorted_by_clue_first_char(self):
        if not self._sorted_by_clue_first_char:
            self._sorted_by_clue_first_char = self.get_data(
                self.json_sorted_by_clue_first_char,
                self.classify_items_by_clue_first_char,
            )
        return self._sorted_by_clue_first_char
