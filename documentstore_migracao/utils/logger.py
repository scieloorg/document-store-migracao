""" module to utils of logger app """
import os
from logging import config as l_config
from documentstore_migracao import config


def configure_logger():

    SUB_DICT_CONFIG = {"level": "DEBUG", "handlers": ["file"], "propagate": False}

    l_config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "level": "INFO",
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": os.path.join(config.get("LOGGER_PATH"), "migracao.log"),
                    "maxBytes": 100 * 1024 * 1024,
                    "backupCount": 3,
                },
            },
            "loggers": {
                "packtools.domain": SUB_DICT_CONFIG,
                "documentstore_migracao.export.sps_package": SUB_DICT_CONFIG,
                "documentstore_migracao.utils.convert_html_body": SUB_DICT_CONFIG,
                "documentstore_migracao.processing.packing": SUB_DICT_CONFIG,
                "documentstore_migracao.processing.conversion": SUB_DICT_CONFIG,
            },
            "root": {"level": "DEBUG", "handlers": ["console", "file"]},
        }
    )
