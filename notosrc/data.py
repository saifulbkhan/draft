# Copyright (C) 2017  Saiful Bari Khan <saifulbkhan@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from notosrc.datamodel import Base, Notebook, Note, Tag
from notosrc.datamodel import USER_DATA_DIR, DB_URL

# TODO: Pass 'echo=True' when debugging
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(engine)


def create_notebook(name):
    with session_scope() as session:
        notebook = Notebook(name)
        session.add(notebook)
        return notebook


def create_note(title, notebook='Misc'):
    with session_scope() as session:
        note = Note(title, notebook)
        session.add(note)
        return note


def delete(entity):
    with session_scope() as session:
        session.delete(entity)
    delete_orphan_tags()


def update(entity, prop, value):
    assert prop not in ['last_modified', 'created']
    with session_scope() as session:
        #TODO: Warn if no prop attr existed before update
        getattr(entity, prop) = value


def update_multi(entity, prop_list, val_list):
    assert len(prop_list) == len(val_list)
    assert 'last_modified' not in prop_list
    assert 'created' not in prop_list
    with session_scope() as session:
        for i, prop in prop_list:
            getattr(entity, prop) = val_list[i]


def fetch_tag(name):
    with session_scope() as session:
        tag = session.query(Tag).\
                filter_by(keyword=name.lower()).\
                one()
        if tag:
            return tag
    return create_tag(name)


def create_tag(name):
    with session_scope() as session:
        tag = Tag(name.lower())
        session.add(Tag)
        return tag


def delete_orphan_tags():
    with engine.connect() as connection:
        orphan_tags_query = text("""
            SELECT keyword
              FROM tag
             WHERE tag.id NOT IN (SELECT tag_id
                                    FROM note_tags)
        """)
        res = connection.execute(orphan_tag_query).fetchall()
        if not res:
            return
        with session_scope() as ssn:
            for i in range(len(res)):
                tag = ssn.query(Tag).filter_by(keyword=res[i][0]).one_or_none()
                ssn.delete(tag)


def fetch_all_notes():
    with session_scope() as session:
        notes = session.query(Note).all()
        return notes


def fetch_notes_not_in_notebooks():
    with session_scope() as session:
        notes = session.query(Notes).\
                filter(Note.notebook==None).\
                all()
        return notebooks


def fetch_notes_in_notebook(notebook):
    with session_scope() as session:
        notes = session.query(Note).\
                filter(Note.notebook==notebook).\
                all()
        return notes


def fetch_all_notebooks():
    with session_scope() as session:
        notebooks = session.query(Notebook).all()
        return notebooks


def fetch_notebooks_not_in_notebook():
    with session_scope() as session:
        notebooks = session.query(Notebook).\
                    filter(Notebook.parent==None).\
                    all()
        return notebooks


def fetch_notebook_in_notebook(notebooks):
    with session_scope() as session:
        notebooks = session.query(Notebook).\
                    filter(Notebook.parent==notebook).\
                    all()
        return notebooks
