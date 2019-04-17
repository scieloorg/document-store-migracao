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
    dest_path = None
    for index, body in enumerate(obj_xml.xpath("//body"), start=1):
        logger.info("Processando body numero: %s" % index)
        medias = xml.find_medias(body)
        if medias:
            is_media = True
            dest_path = files.create_path_by_file(
                config.get("DOWNLOAD_PATH"), file_xml_path
            )

            logger.info("%s possui %s midias", file_xml_path, len(medias))
            for media in medias:
                request_file = request.get(
                    urljoin(config.get("STATIC_URL_FILE"), media)
                )
                filename_m, ext_m = files.extract_filename_ext_by_path(media)
                files.write_file_binary(
                    os.path.join(dest_path, "%s%s" % (filename_m, ext_m)),
                    request_file.content,
                )

    if is_media and dest_path:
        filename, _ = files.extract_filename_ext_by_path(file_xml_path)
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


def read_json_file(file_path: str) -> List[dict]:
    """Ler um arquivo JSON e retorna o resultado
    em formato de estruturas Python"""

    return json.loads(files.read_file(file_path))
