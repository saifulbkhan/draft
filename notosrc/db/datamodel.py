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

from datetime import datetime, timedelta
from hashlib import sha256
from gettext import gettext as _

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship, backref, reconstructor


class Base(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


class TimestampMixin(object):
    created = Column(String)
    last_modified = Column(String)

    def __init__(self):
        self.created = datetime.now().isoformat(timespec='milliseconds')
        self.update_last_modified()

    def update_last_modified(self):
        self.last_modified = datetime.now().isoformat(timespec='milliseconds')

    def get_last_modified_relative_time(self):
        return self._relative_time_string(self.last_modified)

    def get_created_relative_time(self):
        return self._relative_time_string(self.created)

    def get_last_modified_datetime(self):
        return self._datetime_string(self.last_modified)

    def get_created_datetime(self):
        return self._datetime_string(self.created)

    def _relative_time_string(self, dt_str):
        date_time =  datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')
        one_day = timedelta(days=1)
        if date_time.date() == datetime.now().date():
            return (_("Today at %s" % date_time.strftime('%I:%M %p')))
        elif date_time.date() == (datetime.now() - one_day).date():
            return (_("Yesterday at %s" % date_time.strftime('%I:%M %p')))

        return date_time.strftime('%d %b %Y')

    def _datetime_string(self, dt_str):
        date = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f').\
                        strftime('%d %b %Y')
        time = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f').\
                        strftime('%I:%M %p')
        return (date, time)


Base = declarative_base(cls=Base)
note_tags = Table('note_tags', Base.metadata,
                 Column('note_id', ForeignKey('note.id'), primary_key=True),
                 Column('tag_id', ForeignKey('tag.id'), primary_key=True))


class Note(TimestampMixin, Base):
    title = Column(String)
    notebook_id = Column(Integer, ForeignKey('notebook.id'), nullable=True)
    in_trash = Column(Integer)

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
        self.in_trash = 0
        self.move_to_notebook(notebook)
        self.hash_id = sha256(('note%s' % self.id).encode()).hexdigest()

    @reconstructor
    def init_on_load(self):
        self.hash_id = sha256(('note%s' % self.id).encode()).hexdigest()

    def move_to_notebook(self, notebook):
        if notebook:
            assert isinstance(notebook, Notebook)
            self.notebook_id = notebook.id
        else:
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
    parent_id = Column(Integer, ForeignKey('notebook.id'), nullable=True)
    in_trash = Column(Integer)

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
        self.in_trash = 0
        self.move_to_notebook(parent)
        self.hash_id = sha256(('notebook%s' % self.id).encode()).hexdigest()

    @reconstructor
    def init_on_load(self):
        self.hash_id = sha256(('notebook%s' % self.id).encode()).hexdigest()

    def move_to_notebook(self, parent_notebook):
        if parent_notebook:
            assert isinstance(parent_notebook, Notebook)
            self.parent_id = parent_notebook.id
        else:
            self.parent_id = None
