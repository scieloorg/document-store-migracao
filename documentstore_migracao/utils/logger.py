""" module to utils of logger app """
import os
from logging import config as l_config
from documentstore_migracao import config


def configure_logger():
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
                    "level": "ERROR",
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": os.path.join(config.get("LOGGER_PATH"), "migracao.log"),
                    "maxBytes": 100 * 1024 * 1024,
                    "backupCount": 3,
                },
            },
            "loggers": {"": {"level": "DEBUG", "handlers": ["console", "file"]}},
            "disable_existing_loggers": False,
        }
    )
