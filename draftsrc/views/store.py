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

from draftsrc import file, db
from draftsrc.db import data


class DraftListStore(Gio.ListStore):
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
        return '<DraftListStore>'

    def __init__(self, parent_group):
        """Initialises a new DraftListStore for the given parent group. If
        @parent_group is None, orphan texts (not part of any group) are queried.

        @parent_group: string, The unique hash string for the parent group
        """
        Gio.ListStore.__init__(self, item_type=self.RowData.__gtype__)
        self._parent_group = parent_group
        self._load_texts()

    def _load_texts(self):
        """Asks db to fetch the set of texts in @parent_group"""
        self.remove_all()
        with db.connect() as connection:
            load_fn = data.texts_in_group
            kwargs = {'conn': connection, 'group_id': self._parent_group['id']}

            if not self._parent_group['id']:
                load_fn = data.texts_not_in_groups
                kwargs = {'conn': connection}

            for text in load_fn(**kwargs):
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

        @self: DraftListStore model
        """
        id = None
        with db.connect() as connection:
            text_id = data.create_text(connection,
                                       _("Untitled"),
                                       self._parent_group['id'])
            text = data.text_for_id(connection, text_id)
            text_row = self._row_data_for_text(text)
            return self.append(text_row)

    def prepare_for_edit(self, position, switch_view, load_file):
        """Prepare text at @position in @self to be edited.

        @self: DraftListStore model
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

        @self: DraftListStore model
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

        db.async_updater.execution_fn = data.update_text
        db.async_updater.enqueue(id, item.to_dict())

    def set_keywords_for_position(self, position, keywords):
        """Set the keywords for the item at given position

        @self: DraftListStore model
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

    def queue_final_save(self, metadata):
        db.final_updater.execution_fn = data.update_text
        db.final_updater.enqueue(metadata['id'], metadata)

    def delete_item_at_postion(self, position):
        """Delete item at @position in model

        @self: DraftListStore model
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


class Column(object):
    NAME = 0
    CREATED = 1
    LAST_MODIFIED = 2
    IN_TRASH = 3
    ID = 4
    PARENT_ID = 5


class DraftTreeStore(Gtk.TreeStore):
    """Model for storing metadata related to heirarchical group structures"""
    _top_level_iter = None

    def __repr__(self):
        return '<DraftTreeStore>'

    def __init__(self, top_row_name):
        Gtk.TreeStore.__init__(
            self,
            GObject.TYPE_STRING,        # name of group
            GObject.TYPE_STRING,        # date created
            GObject.TYPE_STRING,        # date last modified
            GObject.TYPE_BOOLEAN,       # whether in trash or not
            GObject.TYPE_INT,           # id of the group
            GObject.TYPE_PYOBJECT       # id of the parent group, can be null
        )
        self._append_top_level_row(top_row_name)
        self._load_data()

    def _append_top_level_row(self, top_row_name):
        top_level_group = self._dict_for_top_level_row(top_row_name)
        self._top_level_iter = self._append_group(top_level_group)

    def _load_data(self):
        """Load group data into tree model"""
        with db.connect() as connection:
            for parent_group in data.groups_not_in_groups(connection):
                self._append_group_and_children(connection, parent_group)

    def _append_group_and_children(self, connection, group, treeiter=None):
        """Recursively append to tree with rows for @group and its child
        groups, with @treeiter node as parent

        @connection: sqlite3.connection object, the db connection to reuse
        @group: dict, metadata for group to be recursively inserted
        @treeiter: GtkTreeIter, node iterator where @group and children
                   will be appended
        """
        if group['in_trash']:
            return

        if not treeiter:
            treeiter = self._top_level_iter

        current_iter = self._append_group(group, treeiter)

        for child_group in data.groups_in_group(connection, group['id']):
            self._append_group_and_children(connection, child_group, current_iter)

    def _append_group(self, group, treeiter=None):
        """Append a single group at the given node

        @group: dict, metadata representing group to be appended
        @treeiter: GtkTreeIter, node iterator where @group will be appended
        """
        values = [
            group['name'],
            group['created'],
            group['last_modified'],
            group['in_trash'],
            group['id'],
            group['parent_id']
        ]
        current_iter = self.append(treeiter, values)
        return current_iter

    def get_group_for_iter(self, treeiter):
        """For the given @treeiter return a valid dict with metadata values"""
        if self._iter_is_top_level(treeiter):
            return self._dict_for_top_level_row()

        return self._dict_for_row(treeiter)

    def _dict_for_top_level_row(self, row_name=None):
        if not row_name:
            row_name = self[self._top_level_iter][Column.NAME]
        return {
            'name': row_name,
            'created': None,
            'last_modified': None,
            'in_trash': None,
            'id': None,
            'parent_id': None
        }

    def _dict_for_row(self, treeiter):
        return {
            'name': self[treeiter][Column.NAME],
            'created': self[treeiter][Column.CREATED],
            'last_modified': self[treeiter][Column.LAST_MODIFIED],
            'in_trash': self[treeiter][Column.IN_TRASH],
            'id': self[treeiter][Column.ID],
            'parent_id': self[treeiter][Column.PARENT_ID]
        }

    def _iter_is_top_level(self, treeiter):
        path = self.get_path(treeiter)
        top_level_path = self.get_path(self._top_level_iter)

        if path == top_level_path:
            return True

        return False

    def new_group_request(self, parent_iter=None):
        """Create a new text group and append it to the @parent_iter node"""
        parent_id = None
        if parent_iter and not self._iter_is_top_level(parent_iter):
            parent_id = self[parent_iter][Column.ID]

        with db.connect() as connection:
            group_id = data.create_group(connection, _("New Group"), parent_id)
            group = data.group_for_id(connection, group_id)
            return self._append_group(group, parent_iter)

    def set_prop_for_iter(self, treeiter, prop, value):
        """Set the property @prop to @value for the row given by @treeiter"""
        if self._iter_is_top_level(treeiter):
            return

        assert prop in ['name', 'last_modified', 'in_trash', 'parent_id']

        if prop == 'name':
            self[treeiter][Column.NAME] = value
        elif prop == 'last_modified':
            self[treeiter][Column.LAST_MODIFIED] = value
        elif prop == 'in_trash':
            self[treeiter][Column.IN_TRASH] = value
        elif prop == 'parent_id':
            self[treeiter][Column.PARENT_ID] = value

        values = self._dict_for_row(treeiter)
        group_id = values['id']
        with db.connect() as connection:
            data.update_group(connection, group_id, values)

        if self[treeiter][Column.IN_TRASH]:
            self.remove(treeiter)

        # TODO: update model structure if parent id changed

    def permanently_delete_group_at_iter(self, treeiter):
        """Remove the row @treeiter from model and delete the group for this
        entry from the DB as well"""
        values = self._dict_for_row(treeiter)
        group_id = values['id']
        print(group_id)
        with db.connect() as connection:
            data.delete_group(connection, group_id)

        self.remove(treeiter)
