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

from gettext import gettext as _
from gi.repository import GLib, GObject, Gtk, Gio

from notosrc.db import data
from notosrc import file
from notosrc.datamodel import Note, Notebook


class NotoListStore(Gio.ListStore):
    """Model for a list of notes (only) from one particular note group"""

    class NoteData(GObject.Object):
        """Represents one entry in list of notes"""
        __gtype_name__ = 'NoteData'

        title = ''
        tags = []
        last_modified = ''
        db_id = None
        hash_id = ''
        in_trash = False
        parent_list = []

        @GObject.Property(type=str)
        def prop_title(self):
            return self.title

        @prop_title.setter
        def prop_title(self, value):
            self.title = value

        @GObject.Property(type=GObject.TYPE_PYOBJECT)
        def prop_tags(self):
            return self.tags

        @prop_tags.setter
        def prop_tags(self, value):
            self.tags = value

        @GObject.Property(type=str)
        def prop_last_modified(self):
            return self.last_modified

        @prop_last_modified.setter
        def prop_last_modified(self, value):
            self.last_modified = value

        @GObject.Property(type=int)
        def prop_db_id(self):
            return self.db_id

        @prop_db_id.setter
        def prop_db_id(self, value):
            self.db_id = value

        @GObject.Property(type=str)
        def prop_hash_id(self):
            return self.hash_id

        @prop_hash_id.setter
        def prop_hash_id(self, value):
            self.hash_id = value

        @GObject.Property(type=bool, default=False)
        def prop_in_trash(self):
            return self.in_trash

        @prop_in_trash.setter
        def prop_in_trash(self, value):
            self.in_trash = value

        @GObject.Property(type=GObject.TYPE_PYOBJECT)
        def prop_parent_list(self):
            return self.parent_list

        @prop_parent_list.setter
        def prop_parent_list(self, value):
            self.parent_list = value

        def to_dict(self):
            return {
                'title': self.title,
                'tags': self.tags,
                'last-modified': self.last_modified,
                'db-id': self.db_id,
                'hash-str': self.hash_id,
                'in-trash': self.in_trash,
                'parent-list': self.parent_list
            }

    def __repr__(self):
        return '<NotoListStore>'

    def __init__(self, parent_group):
        """Initialises a new NotoListStore for the given parent group. If
        @parent_group is None, orphan notes (not part of any group) are queried.

        @parent_group: string, The unique hash string for the parent group
        """
        Gio.ListStore.__init__(self, item_type=self.NoteData.__gtype__)
        self._parent_group = parent_group
        self._load_notes(parent_group)

    def _load_notes(self, parent):
        """Asks db to fetch the set of notes in @parent group"""
        with data.session_scope() as session:
            notes = data.fetch_notes_not_in_notebooks(session)
            for note in notes:
                row = self._row_data_for_note(note)
                if not row.in_trash:
                    self.append(row)

    def _row_data_for_note(self, note):
        """Create NoteData for one note"""
        tags = map(lambda x: x.keyword, note.tags)
        hash_list = self._get_parent_hash_list(note)

        note_data = self.NoteData()
        note_data.prop_title = note.title
        note_data.prop_tags = tags
        note_data.prop_last_modified = note.get_last_modified_relative_time()
        note_data.prop_db_id = note.id
        note_data.prop_hash_id = note.hash_id
        note_data.prop_in_trash = bool(note.in_trash)
        note_data.prop_parent_list = hash_list

        return note_data

    def _get_parent_hash_list(self, entity, parent_id='notebook_id'):
        """Returns a list of hash strings for parent groups that joined
        together can form a relative path to note dir.
        """
        hashes = []
        while getattr(entity, parent_id):
            notebook_id = getattr(entity, parent_id)
            entity = fetch_notebook_by_id(notebook_id)
            hashes.append(entity.hash_id)
        hashes.reverse()
        return hashes

    def new_note_request(self):
        """Request for a new note

        @self: NotoListStore model
        """
        id = None
        with data.session_scope() as session:
            note = Note(_("Untitled"), self._parent_group)
            session.add(note)
            # premature commit to ensure we get proper id
            session.commit()
            id = note.id

        # new session needed for fetch by id, hopefully will be able to avoid
        # all this when we move away from sqlalchemy
        with data.session_scope() as session:
            note = data.fetch_note_by_id(id, session)
            note_row = self._row_data_for_note(note)
            return self.append(note_row)

    def prepare_for_edit(self, position, switch_view, load_file):
        """Prepare note at @position in @self to be edited.

        @self: NotoListStore model
        @position: integer, position at which the item to be edited is located
                   in the model
        @switch_view: method, called to check if a new editor buffer is needed
        @load_file: method, passed on to `file.read_file_contents` function
        """
        item = self.get_item(position)
        id = item.prop_db_id
        buffer = switch_view(str(id))
        if not buffer:
            return

        hash_id = item.prop_hash_id
        parent_hashes = list(item.prop_parent_list)
        file.read_file_contents(hash_id, parent_hashes, buffer, load_file)

    def set_title_for_position(self, position, title):
        """Modify title for item at @position in @title

        @self: NotoListStore model
        @position: integer, position at which item is located
        @title: string, new value for item's title
        """
        item = self.get_item(position)
        id = item.prop_db_id
        item.prop_title = title
        # TODO: 'notify' view that a prop for an item has changed

        with data.session_scope() as session:
            note = data.fetch_note_by_id(id, session)
            note.title = title

    def delete_item_at_postion(self, position):
        """Delete item at @position in model

        @self: NotoListStore model
        @position: integer, position at which the item to be deleted is located
        """
        item = self.get_item(position)
        id = item.prop_db_id
        hash_id = item.prop_hash_id
        parent_hashes = item.prop_parent_list

        self.remove(position)
        file.trash_file(hash_id, parent_hashes)

        with data.session_scope() as session:
            note = data.fetch_note_by_id(id, session)
            note.in_trash = True


class TreeStore(Gtk.TreeStore):

    def __repr__(self):
        return '<TreeStore>'

    def __init__(self):
        Gtk.TreeStore.__init__(
            self,
            GObject.TYPE_STRING,        # title or name
            GObject.TYPE_STRING,        # tags or number of items
            GObject.TYPE_STRING,        # last modified
            GObject.TYPE_INT,           # id for the entity
            GObject.TYPE_STRING,        # hash-id for file or folder name
            GObject.TYPE_BOOLEAN,       # whether in trash or not
            GObject.TYPE_PYOBJECT       # list of parent hashes
        )
        self._load_data()

    def _load_data(self):
        # TODO: add notebooks
        pass

    def new_notebook_request(self):
        id = None
        with data.session_scope() as session:
            notebook = Notebook(name=_("Untitled"))
            session.add(notebook)
            # premature commit
            session.commit()
            id = notebook.id
        with data.session_scope() as session:
            notebook = data.fetch_notebook_by_id(id, session)
            notebook_row = self.row_for_notebook(notebook)
            self.append(None, notebook_row)

    def row_for_notebook(self, notebook):
        items = len(notebook.notes) + len(notebook.notebooks)
        row = [notebook.name,
               str(items),
               notebook.get_last_modified_relative_time(),
               notebook.id,
               notebook.hash_id,
               bool(notebook.in_trash)]
        return row

    def rows_for_notebooks(self, notebooks):
        rows = []
        for notebook in notebooks:
            row = self.row_for_notebook(notebook)
            rows.append(row)
        return rows

    def get_parent_hash_list(self, entity, parent_id='notebook_id'):
        hashes = []
        while getattr(entity, parent_id):
            notebook_id = getattr(entity, parent_id)
            entity = fetch_notebook_by_id(notebook_id)
            hashes.append(entity.hash_id)
        hashes.reverse()
        return hashes
