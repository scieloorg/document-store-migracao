import logging
import os

from mongoengine import connect
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from opac_schema.v1.models import Journal

from documentstore_migracao import config, exceptions
from documentstore_migracao.utils import files, request


logger = logging.getLogger(__name__)


Base = declarative_base()


class Image(Base):
    """Image Model
    CREATE TABLE image (
        id INTEGER NOT NULL,
        name VARCHAR(64) NOT NULL,
        path VARCHAR(256) NOT NULL,
        language VARCHAR(255),
        PRIMARY KEY (id)
    );
    """
    __tablename__ = 'image'
    id = Column(Integer, Sequence('image_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)
    path = Column(String(256), nullable=False)
    language = Column(String(255))

    def __repr__(self):
        return '<Image(id="%s", name="%s", path="%s")>' % (
            self.id, self.name, self.path
        )


def connect_to_databases(mongodb_uri, mongodb_db, sqlite_db):
    """Connect to Website MongoDB and SQLite"""
    logger.info("Connecting to %s/%s", mongodb_uri, mongodb_db)
    connect(db=mongodb_db, host=mongodb_uri)

    logger.info("Connecting to %s", sqlite_db)
    engine = create_engine(sqlite_db)
    Session = sessionmaker(bind=engine)
    return Session()


def migrate_logos_to_website(session, website_img_dir):
    """Read all Journals from Website MongoDB collection and, for each one, get journal
    logo from current website, save to website media directory, create an image record
    in SQLite Image Table and update journal document with logo URL.

    session: SQLite DB session created in `connect_to_databases`
    website_img_dir: Website media directory
    """
    journals = Journal.objects.all()
    if len(journals) == 0:
        raise exceptions.NoJournalInWebsiteError(
            "No journals in Website Database. Migrate Isis Journals first."
        )

    for journal in journals:
        logger.debug("Journal acronym %s", journal.acronym)
        logo_old_filename = "glogo.gif"
        logo_url = "{}img/revistas/{}/glogo.gif".format(
            config.get("STATIC_URL_FILE"), journal.acronym
        )
        try:
            logger.debug("Getting Journal logo in %s", logo_url)
            request_file = request.get(
                logo_url, timeout=int(config.get("TIMEOUT") or 10)
            )
        except request.HTTPGetError as e:
            try:
                msg = str(e)
            except TypeError:
                msg = "Unknown error"
            logger.error(msg)
        else:
            logo_filename =  "_".join([journal.acronym, logo_old_filename])
            dest_path_file = os.path.join(website_img_dir, logo_filename)
            logger.debug("Saving Journal logo in %s", dest_path_file)
            files.write_file_binary(dest_path_file, request_file.content)

            image_path = "images/%s" % logo_filename
            logger.debug("Saving logo as image in %s", image_path)
            session.add(Image(name=logo_filename, path=image_path))
            session.commit()

            journal.logo_url = "/media/%s" % image_path
            logger.debug("Updating Journal with logo_url %s", journal.logo_url)
            journal.save()
