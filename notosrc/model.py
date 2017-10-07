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

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Table
from sqlalchemy.orm import relationship

from gi.repository import GLib

USER_DATA_DIR = os.path.join(GLib.get_user_data_dir(), 'noto')
db_url = 'sqlite:///' + os.path.join(USER_DATA_DIR, 'noto.db')

class Base(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


class TimestampMixin(object):
    # date and time in SQLite are represented in string format
    created = Column(String)
    last_modified = Column(String)

Base = declarative_base(cls=Base)
note_tags = Table('note_tags', Base.metadata,
                 Column(Integer, ForeignKey('note.id'), primary_key=True),
                 Column(Integer, ForeignKey('tag.id'), primary_key=True))

class Note(TimestampMixin, Base):
    title = Column(String)
    notebook_id = Column(Integer, ForeignKey('notebook.id'))

    tags = relationship('Tag', secondary=note_tags, back_populates='notes')
    notebook = relationship('Notebook', back_populates='notes')

    def __repr__(self):
        return '<Note(title=%s, created=%s, last_changed=%s)>' % (
            self.title,
            self.created,
            self.last_modified
        )


class Tag(Base):
    name = Column(string)
    notes = relationship('Note', secondary=note_tags, back_populates='tags')

    def __repr__(self):
        return '<Note(name=%s)>' % self.name


class Notebook(TimestampMixin, Base):
    name = Column(String)
    notes = relationship('Note', back_populates='notebook', lazy='dynamic')

    def __repr__(self):
        return '<Notebook(name=%s, created=%s, last_modified=%s)>' % (
            self.name,
            self.created,
            self.last_modified
        )

# TODO: Pass 'echo=True' when debugging
engine = create_engine(DB_URL)
Base.metadata.create_all(engine)
