import os
import logging
import json
from typing import List

from requests.compat import urljoin
from lxml import etree
from documentstore_migracao.utils import files, xml, request, string
from documentstore_migracao import config, exceptions


logger = logging.getLogger(__name__)


def reading_article_xml(file_xml_path, move_success=True):

    article = files.read_file(file_xml_path)
    obj_xml = etree.fromstring(article)

    is_media = False
    for index, body in enumerate(obj_xml.xpath("//body"), start=1):
        logger.info("Processando body numero: %s" % index)
        medias = xml.find_medias(body)
        if medias:
            is_media = True
            logger.info("%s possui midias", file_xml_path)

            for media in medias:

                # import pdb;pdb.set_trace()

                request_file = request.get(
                    urljoin(config.get("STATIC_URL_FILE"), media)
                )

                filename, _ = string.extract_filename_ext_by_path(file_xml_path)
                dest_path = os.path.join(config.get("CONVERSION_PATH"), filename)
                files.create_dir(dest_path)

                filename_m, ext_m = string.extract_filename_ext_by_path(media)
                x = os.path.join(dest_path, "%s%s" % (filename_m, ext_m))

                files.write_file_bynary(x, request_file.content)

    if is_media:
        files.write_file(
            os.path.join(dest_path, "%s.xml" % (filename)),
            xml.prettyPrint_format(
                string.remove_spaces(
                    etree.tostring(
                        obj_xml,
                        doctype=config.DOC_TYPE_XML,
                        pretty_print=True,
                        xml_declaration=True,
                        encoding="utf-8",
                        method="xml",
                    ).decode("utf-8")
                )
            ),
        )

    if move_success:
        files.move_xml_conversion2success(
            file_xml_path.replace(config.get("CONVERSION_PATH"), "")
        )


def reading_article_ALLxml():

    logger.info("Iniciando Leituras do xmls")
    list_files_xmls = files.xml_files_list(config.get("CONVERSION_PATH"))
    for file_xml in list_files_xmls:

        try:
            reading_article_xml(
                os.path.join(config.get("CONVERSION_PATH"), file_xml),
                move_success=False,
            )

        except Exception as ex:
            logger.error(file_xml)
            logger.exception(ex)


def read_journals_from_json(file_path: str = "title.json") -> List[dict]:
    """Ler um arquivo json contendo uma lista de periódicos e
    retorna os dados dos periódicos em formato de tipos Python

    :param `file_path`: Complemento de path para o arquivo json de periódicos
    """

    json_path = os.path.join(config.get("SOURCE_PATH"), file_path)

    return json.loads(files.read_file(json_path))
