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

import os.path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from gi.repository import GLib, Gio

from notosrc.datamodel import Base, Notebook, Note, Tag

USER_DATA_DIR = os.path.join(GLib.get_user_data_dir(), 'noto')
DB_URL = 'sqlite:///' + os.path.join(USER_DATA_DIR, 'noto.db')

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
    try:
        note_dir = os.path.join(USER_DATA_DIR, 'notes')
        note_local_dir = os.path.join(note_dir, 'local')
        note_trash_dir = os.path.join(note_dir, '.trash')
        Gio.file_new_for_path(note_dir).make_directory()
        Gio.file_new_for_path(note_local_dir).make_directory()
        Gio.file_new_for_path(note_local_dir).make_directory()
    except Exception as e:
        # TODO: Warn folder already exists or creation failed
        return


def create_notebook(name, session):
    notebook = Notebook(name)
    session.add(notebook)
    return notebook


def create_note(title, session, notebook=None):
    note = Note(title, notebook)
    session.add(note)
    return note


def fetch_tag(name, session):
    tag = session.query(Tag).\
            filter_by(keyword=name.lower()).\
            one()
    if tag:
        return tag
    return create_tag(name)


def create_tag(name, session):
    tag = Tag(name.lower())
    session.add(Tag)
    return tag


def delete_orphan_tags(session):
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
        for i in range(len(res)):
            tag = session.query(Tag).filter_by(keyword=res[i][0]).one_or_none()
            ssesion.delete(tag)


def fetch_notebook_by_id(notebook_id, session):
    notebook = session.query(Notebook).\
               filter(Notebook.id==notebook_id).\
               one_or_none()


def fetch_all_notes(session):
    notes = session.query(Note).all()
    return notes


def fetch_notes_not_in_notebooks(session):
    notes = session.query(Note).\
            filter(Note.notebook_id==None).\
            all()
    return notes


def fetch_notes_in_notebook(notebook, session):
    notes = session.query(Note).\
            filter(Note.notebook_id==notebook.id).\
            all()
    return notes


def fetch_all_notebooks(session):
    notebooks = session.query(Notebook).all()
    return notebooks


def fetch_notebooks_not_in_notebook(session):
    notebooks = session.query(Notebook).\
                filter(Notebook.parent_id==None).\
                all()
    return notebooks


def fetch_notebook_in_notebook(notebooks, session):
    notebooks = session.query(Notebook).\
                filter(Notebook.parent_id==notebook.id).\
                all()
    return notebooks
