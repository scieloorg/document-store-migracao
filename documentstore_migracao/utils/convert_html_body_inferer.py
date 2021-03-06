import json
import os

from documentstore_migracao import config
from documentstore_migracao.utils import files


class Inferer:

    REFTYPE = {"table-wrap": "table", "ref": "bibr"}

    OTHER_SECTIONS = [
        "text",
    ]

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
            for clue, tag in self.rules.sorted_rules:
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
            if a_href_text[:4] in self.OTHER_SECTIONS:
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
            clue_and_tag_items = self.rules.sorted_rules
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
        self.inferer_clue_json_file_path = os.path.join(
            dirname, "_inferer_clue.json")
        self._inferer_tags_json_file_path = os.path.join(
            dirname, "_inferer_tags.json")
        self._rules = None
        self._sorted_rules = None
        self._sorted_by_clue_len_in_reverse_order = None
        self._sorted_by_tag = None
        self._sorted_by_clue_first_char = None

    def _is_out_of_date(self, file_path):
        if not os.path.isfile(file_path):
            return True
        return os.stat(file_path).st_mtime < os.stat(self.rules_file_path).st_mtime

    @property
    def rules(self):
        if not self._rules:
            with open(self.rules_file_path, "r") as fp:
                self._rules = (
                    tuple(item.strip().split("|")) for item in fp.readlines()
                )
        return self._rules

    @property
    def sorted_by_clue_len_in_reverse_order(self):
        if not self._sorted_by_clue_len_in_reverse_order:
            self._sorted_by_clue_len_in_reverse_order = sorted(
                [
                    (len(text), text, tag)
                    for text, tag in self.rules
                ],
                reverse=True,
            )
        return self._sorted_by_clue_len_in_reverse_order

    @property
    def sorted_rules(self):
        if not self._sorted_rules:
            self._sorted_rules = [
                (text, tag)
                for lent, text, tag in self.sorted_by_clue_len_in_reverse_order
            ]
        return self._sorted_rules

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
        if self._is_out_of_date(json_file_path):
            data = classification_function()
            with open(json_file_path, "w") as fp:
                fp.write(json.dumps(data))
        else:
            with open(json_file_path, "r") as fp:
                data = json.loads(fp.read())
        return data

    @property
    def sorted_by_tag(self):
        if not self._sorted_by_tag:
            self._sorted_by_tag = self.get_data(
                self._inferer_tags_json_file_path, self.classify_items_by_tag
            )
        return self._sorted_by_tag

    @property
    def sorted_by_clue_first_char(self):
        if not self._sorted_by_clue_first_char:
            self._sorted_by_clue_first_char = self.get_data(
                self.inferer_clue_json_file_path,
                self.classify_items_by_clue_first_char,
            )
        return self._sorted_by_clue_first_char
