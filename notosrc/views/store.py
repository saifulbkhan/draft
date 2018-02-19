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

from notosrc import file, db
from notosrc.db import data


class NotoListStore(Gio.ListStore):
    """Model for a list of texts (only) from one particular text group"""

    class RowData(GObject.Object):
        """Represents one entry in list of texts"""
        __gtype_name__ = 'RowData'

        title = ''
        keywords = []
        last_modified = ''
        db_id = None
        hash_id = ''
        in_trash = False
        parent_id = None
        parent_list = []
        markup = None
        subtitle = None
        word_goal = None
        last_edit_position = None

        @GObject.Property(type=str)
        def prop_title(self):
            return self.title

        @prop_title.setter
        def prop_title(self, value):
            self.title = value

        @GObject.Property(type=GObject.TYPE_PYOBJECT)
        def prop_keywords(self):
            return self.keywords

        @prop_keywords.setter
        def prop_keywords(self, value):
            self.keywords = value

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

        @GObject.Property(type=int)
        def prop_parent_id(self):
            return self.parent_id

        @prop_parent_id.setter
        def prop_parent_id(self, value):
            self.parent_id = value

        @GObject.Property(type=GObject.TYPE_PYOBJECT)
        def prop_parent_list(self):
            return self.parent_list

        @prop_parent_list.setter
        def prop_parent_list(self, value):
            self.parent_list = value

        @GObject.Property(type=str)
        def prop_markup(self):
            return self.markup

        @prop_markup.setter
        def prop_markup(self, value):
            self.markup = value

        @GObject.Property(type=str)
        def prop_subtitle(self):
            return self.subtitle

        @prop_subtitle.setter
        def prop_subtitle(self, value):
            self.subtitle = value

        @GObject.Property(type=int)
        def prop_word_goal(self):
            return self.word_goal

        @prop_word_goal.setter
        def prop_word_goal(self, value):
            self.word_goal = value

        @GObject.Property(type=int)
        def prop_last_edit_position(self):
            return self.last_edit_position

        @prop_last_edit_position.setter
        def prop_last_edit_position(self, value):
            self.last_edit_position = value

        def from_dict(self, data_dict):
            self.title = data_dict['title']
            self.keywords = data_dict['keywords']
            self.last_modified = data_dict['last_modified']
            self.db_id = data_dict['id']
            self.hash_id = data_dict['hash_id']
            self.in_trash = bool(data_dict['in_trash'])
            self.parent_id = data_dict['parent_id']
            self.parent_list = data_dict['parents']
            self.markup = data_dict['markup']
            self.subtitle = data_dict['subtitle']

            if data_dict['word_goal']:
                self.word_goal = int(data_dict['word_goal'])
            else:
                self.word_goal = 0

            if data_dict['last_edit_position']:
                self.last_edit_position = int(data_dict['last_edit_position'])
            else:
                self.last_edit_position = 0

        def to_dict(self):
            return {
                'title': self.title,
                'keywords': self.keywords,
                'last_modified': self.last_modified,
                'id': self.db_id,
                'hash_id': self.hash_id,
                'in_trash': int(self.in_trash),
                'parent_id': self.parent_id,
                'parent_list': self.parent_list,
                'markup': self.markup,
                'subtitle': self.subtitle,
                'word_goal': int(self.word_goal),
                'last_edit_position': int(self.last_edit_position)
            }

    def __repr__(self):
        return '<NotoListStore>'

    def __init__(self, parent_group):
        """Initialises a new NotoListStore for the given parent group. If
        @parent_group is None, orphan texts (not part of any group) are queried.

        @parent_group: string, The unique hash string for the parent group
        """
        Gio.ListStore.__init__(self, item_type=self.RowData.__gtype__)
        self._parent_group = parent_group
        self._load_texts(parent_group)

    def _load_texts(self, parent):
        """Asks db to fetch the set of texts in @parent group"""
        with db.connect() as connection:
            for text in data.texts_not_in_groups(connection):
                row = self._row_data_for_text(text)
                if not row.in_trash:
                    self.append(row)

    def _row_data_for_text(self, text_metadata):
        """Create RowData for one text document. Expects a dict of metadata"""
        row_data = self.RowData()
        row_data.from_dict(text_metadata)
        return row_data

    def new_text_request(self):
        """Request for a new text

        @self: NotoListStore model
        """
        id = None
        with db.connect() as connection:
            text_id = data.create_text(connection,
                                       _("Untitled"),
                                       self._parent_group)
            text = data.text_for_id(connection, text_id)
            text_row = self._row_data_for_text(text)
            return self.append(text_row)

    def prepare_for_edit(self, position, switch_view, load_file):
        """Prepare text at @position in @self to be edited.

        @self: NotoListStore model
        @position: integer, position at which the item to be edited is located
                   in the model
        @switch_view: method, called to check if a new editor buffer is needed
        @load_file: method, passed on to `file.read_file_contents` function
        """
        item = self.get_item(position)
        id = item.prop_db_id
        buffer = switch_view(item.to_dict())
        if not buffer:
            return

        hash_id = item.prop_hash_id
        parent_hashes = list(item.prop_parent_list)
        file.read_file_contents(hash_id, parent_hashes, buffer, load_file)

    def set_prop_for_position(self, position, prop, value):
        """Set property @prop for item at @position to @value

        @self: NotoListStore model
        @position: integer, position at which item is located
        @prop: string, property to be set
        @value: obj, value to be assigned to @prop
        """
        if prop == 'keywords':
            return self.set_keywords_for_position(position, value)

        item = self.get_item(position)
        id = item.prop_db_id
        setattr(item, 'prop_' + prop, value)
        # TODO: 'notify' view that a prop for an item has changed

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

    def set_keywords_for_position(self, position, keywords):
        """Set the keywords for the item at given position

        @self: NotoListStore model
        @position: integer, position at which  item is located
        @keywords: list, the collection of strings as keywords for the item
        """
        item = self.get_item(position)
        item.prop_keywords = keywords
        id = item.prop_db_id

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

            # update keywords after, they have been updated in db
            item.prop_keywords = data.fetch_keywords_for_text(connection, id)

        return item.prop_keywords

    def delete_item_at_postion(self, position):
        """Delete item at @position in model

        @self: NotoListStore model
        @position: integer, position at which the item to be deleted is located
        """
        item = self.get_item(position)
        id = item.prop_db_id
        hash_id = item.prop_hash_id
        parent_hashes = item.prop_parent_list
        item.prop_in_trash = True

        self.remove(position)
        file.trash_file(hash_id, parent_hashes)

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())


class TreeStore(Gtk.TreeStore):

    def __repr__(self):
        return '<TreeStore>'

    def __init__(self):
        Gtk.TreeStore.__init__(
            self,
            GObject.TYPE_STRING,        # title or name
            GObject.TYPE_STRING,        # keywords or number of items
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
        items = len(notebook.texts) + len(notebook.notebooks)
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
