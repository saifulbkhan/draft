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
from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from gi.repository import GLib

USER_DATA_DIR = os.path.join(GLib.get_user_data_dir(), 'noto')
DB_URL = 'sqlite:///' + os.path.join(USER_DATA_DIR, 'noto.db')


class Base(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


class TimestampMixin(object):
    # date and time in SQLite are represented in string format
    created = Column(String)
    last_modified = Column(String)

    def __init__(self):
        self.created = datetime.now().isoformat(timespec='milliseconds')
        self.update_last_modified()

    def update_last_modified(self):
        self.last_modified = datetime.now().isoformat(timespec='milliseconds')


Base = declarative_base(cls=Base)
note_tags = Table('note_tags', Base.metadata,
                 Column('note_id', ForeignKey('note.id'), primary_key=True),
                 Column('tag_id', ForeignKey('tag.id'), primary_key=True))


class Note(TimestampMixin, Base):
    title = Column(String)
    notebook_id = Column(Integer, ForeignKey('notebook.id'), nullable=True)

    tags = relationship('Tag',
                        secondary=note_tags,
                        back_populates='notes')
    notebook = relationship('Notebook', back_populates='notes')

    def __repr__(self):
        return '<Note(title=%r, created=%r, last_changed=%r notebook=%r)>' % (
            self.title,
            self.created,
            self.last_modified,
            self.notebook
        )

    def __init__(self, title, notebook=None):
        TimestampMixin.__init__(self)
        self.title = title
        self.move_to_notebook(notebook)

    def move_to_notebook(self, notebook):
        if notebook:
            assert isinstance(notebook, Notebook)
            self.notebook = notebook
            self.notebook_id = notebook.id
        else:
            self.notebook = None
            self.notebook_id = None


class Tag(Base):
    keyword = Column(String)
    notes = relationship('Note', secondary=note_tags, back_populates='tags')

    def __repr__(self):
        return '<Tag(name=%r)>' % self.keyword

    def __init__(self, name):
        self.keyword = name


class Notebook(TimestampMixin, Base):
    name = Column(String)
    parent_id = Column(Integer, ForeignKey('notebook.id'))

    notes = relationship('Note',
                         back_populates='notebook',
                         cascade='all, delete-orphan',
                         lazy='dynamic')
    notebooks = relationship('Notebook',
                             primaryjoin='Notebook.id==remote(Notebook.parent_id)',
                             backref=backref('parent', remote_side=[Base.id]),
                             cascade='all, delete-orphan',
                             lazy='joined',
                             join_depth=2)

    def __repr__(self):
        return '<Notebook(name=%r, created=%r, last_modified=%r)>' % (
            self.name,
            self.created,
            self.last_modified
        )

    def __init__(self, name, parent=None):
        TimestampMixin.__init__(self)
        self.name = name
        self.move_to_notebook(parent)

    def move_to_notebook(self, parent_notebook):
        if parent_notebook:
            assert isinstance(parent_notebook, Notebook)
            self.parent = parent_notebook
            self.parent_id = parent_notebook.id
        else:
            self.parent = None
            self.parent_id = None
