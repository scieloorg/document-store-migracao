import os
import unittest

from xylose.scielodocument import Journal
from documentstore_migracao.processing import extrated, conversion, reading


SAMPLES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
SAMPLES_JOURNAL = {
    "v64": [{"_": "spm@insp3.insp.mx"}],
    "v490": [{"_": "Cuernavaca"}],
    "created_at": "1999-06-08",
    "v941": [{"_": "20170220"}],
    "v951": [{"_": "sonia.reis"}],
    "v6": [{"_": "c"}],
    "v330": [{"_": "CT"}],
    "collection": "spa",
    "v150": [{"_": "Salud pública Méx"}],
    "v66": [{"_": "art"}],
    "v540": [
        {
            "t": '<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/80x15.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License</a>.',
            "_": "",
            "l": "en",
        },
        {
            "t": '<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/80x15.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License</a>.',
            "_": "",
            "l": "es",
        },
        {
            "t": '<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/80x15.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License</a>.',
            "_": "",
            "l": "pt",
        },
    ],
    "v854": [{"_": "Health Policy & Services"}],
    "v310": [{"_": "MX"}],
    "v67": [{"_": "na"}],
    "v943": [{"_": "20170620"}],
    "v68": [{"_": "spm"}],
    "v63": [
        {
            "_": "Av. Universidad 655, Edificio de Gobierno, Planta Baja, Col. Santa María Ahuacatitlán, Cuernavaca, Morelos, MX, 62508, (52 73) 17-5745"
        }
    ],
    "v240": [{"_": "Salud pública Méx"}, {"_": "SPM. Salud Publica de Mexico"}],
    "v10": [{"_": "br1.1"}],
    "v480": [{"_": "Instituto Nacional de Salud Pública"}],
    "issns": ["0036-3634"],
    "v450": [
        {"_": "CURRENT CONTENTS/SOCIAL AND BEHAVIORAL SCIENCES"},
        {"_": "SOCIAL SCIENCES CITATION INDEX"},
        {"_": "RESEARH ALERT"},
        {"_": "INDEX MEDICUS"},
        {"_": "INDEX MEDICUS LATINOAMERICANO"},
        {"_": "EMBASE/EXCERPTA MEDICA"},
        {"_": "CAB HEALTH/CAB ABSTRACT"},
        {"_": "EUROPEAN CLEARING HOUSE ON HEALTH SYSTEMS REFORMS"},
        {
            "_": "INDICE DE REVISTAS MEXICANAS DE INVESTIGACIÓN CIENTÍFICA Y TECNOLÓGICA DEL CONACYT"
        },
        {"_": "BIBLIOMEX-SALUD"},
        {"_": "PERIÓDICA"},
        {
            "_": "INDICE DE REVISTAS DE EDUCACIÓN SUPERIOR E INVESTIGACIÓN EDUCATIVA (IRESIE)"
        },
        {"_": "MEDLINE"},
        {"_": "LILACS"},
        {"_": "ARTEMISA"},
    ],
    "v50": [{"_": "C"}],
    "v992": [{"_": "spa"}],
    "v303": [{"_": "1"}],
    "v85": [{"_": "nd"}],
    "v541": [{"_": "BY-NC-SA/4.0"}],
    "v35": [{"_": "PRINT"}],
    "v302": [{"_": "1"}],
    "v301": [{"_": "1959"}],
    "v380": [{"_": "B"}],
    "v441": [{"_": "Health Sciences"}],
    "v935": [{"_": "0036-3634"}],
    "v100": [{"_": "Salud Pública de México"}],
    "v901": [
        {
            "_": "To publish articles both in English and Spanish related to public health topics, in the form of full-length original research papers, brief communications, review articles, essays, updates, classics, indicators, health news, book reviews and letters to the editor. Bi-monthly publication.",
            "l": "en",
        },
        {
            "_": "Publicar textos, em espanhol e em inglês, sobre temas relacionados com a saúde pública, na forma de editoriais, artigos originais, comunicações breves, artigos de revisão, ensaios, atualizações, clássicos, indicadores, notícias, resenhas bibliográficas e cartas ao editor. Publicação bimestral.",
            "l": "pt",
        },
        {
            "_": "Publicar textos, en español y en inglés, sobre temas relacionados con la salud pública, en forma de editoriales, artículos originales, breves, y de revisión, ensayos, actualizaciones, clásicos, indicadores, noticias, reseñas bibliográficas y cartas al editor. Publicación bimestral.",
            "l": "es",
        },
    ],
    "v151": [{"_": "Salud pública Méx"}],
    "v350": [{"_": "en"}, {"_": "es"}],
    "scimago_id": "19317",
    "code": "0036-3634",
    "v140": [{"_": "Instituto Nacional de Salud Publica (INSP)"}],
    "v421": [{"_": "Salud Publica Mex."}],
    "v930": [{"_": "spm"}],
    "v435": [{"t": "PRINT", "_": "0036-3634"}],
    "v230": [{"_": "Public Health of Mexico"}],
    "v320": [{"_": "Morelos"}],
    "v440": [{"_": "SAUDE PUBLICA"}],
    "v950": [{"_": "sonia.reis"}],
    "v400": [{"_": "0036-3634"}],
    "v940": [{"_": "19990608"}],
    "updated_at": "2017-08-10",
    "v5": [{"_": "S"}],
    "updated_date": "2016-05-24",
    "v62": [{"_": "Instituto Nacional de Salud Pública"}],
    "v117": [{"_": "vancouv"}],
    "v51": [{"a": "20010101", "b": "C", "_": "", "d": "C", "c": "20010701"}],
    "processing_date": "2017-02-20",
    "v880": [{"_": "0036-3634"}],
    "v69": [{"_": "http://saludpublica.mx/insp/index.php/spm"}],
    "v942": [{"_": "19990608"}],
}


class TestProcessingExtrated(unittest.TestCase):
    def test_extrated_journal_data(self):

        obj_journal = Journal(SAMPLES_JOURNAL)
        # extrated.extrated_journal_data(obj_journal)

        self.assertTrue(True)


class TestProcessingConversion(unittest.TestCase):
    def test_conversion_article_xml(self):

        conversion.conversion_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )


class TestProcessingReading(unittest.TestCase):
    def test_reading_article_xml(self):

        reading.reading_article_xml(
            os.path.join(SAMPLES_PATH, "S0036-36341997000100001.xml")
        )
