from db.models import *  # noqa

import os

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from constants import BASE_DIR

sqlite_path = 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'db.sqlite3'))

engine = create_engine(sqlite_path)

# It will create tables if they are not exist
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

sql_session = Session()
