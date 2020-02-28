import logging

from mongoengine import connect
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


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

