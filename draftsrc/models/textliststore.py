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

from gi.repository import GObject, Gtk, Gio

from draftsrc import file, db
from draftsrc.db import data


class DraftTextListStore(Gio.ListStore):
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
        id = item.db_id
        buffer = switch_view(item.to_dict())
        if not buffer:
            return

        hash_id = item.hash_id
        parent_hashes = list(item.parent_list)
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
        elif prop == 'parent_id':
            return self.set_parent_for_position(position, value)

        item = self.get_item(position)
        id = item.db_id
        setattr(item, prop, value)
        # TODO: 'notify' view that a prop for an item has changed

        db.async_updater.execution_fn = data.update_text
        db.async_updater.enqueue(id, item.to_dict())

    def set_parent_for_position(self, position, parent):
        """Set the parent id for text at given position and move the text to
        the corresponding folder"""
        item = self.get_item(position)
        item.parent_id = parent
        id = item.db_id

        with db.connect() as connection:
            text = data.text_for_id(connection, id)
            text_file_name = text['hash_id']
            text_file_parents = text['parents']
            group_dir_parents = []
            if parent is not None:
                group = data.group_for_id(connection, parent)
                group_dir_name = group['hash_id']
                group_dir_parents = group['parents']
                group_dir_parents.append(group_dir_name)

                # update group just to update its last modified status
                data.update_group(connection, parent, group)

            file.move_file(text_file_name, text_file_parents, group_dir_parents)

            data.update_text(connection, id, item.to_dict())

        if parent != self._parent_group:
            self.remove(position)
        return item.db_id

    def set_keywords_for_position(self, position, keywords):
        """Set the keywords for the item at given position

        @self: DraftListStore model
        @position: integer, position at which  item is located
        @keywords: list, the collection of strings as keywords for the item
        """
        item = self.get_item(position)
        item.keywords = keywords
        id = item.db_id

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

            # update keywords after, they have been updated in db
            item.keywords = data.fetch_keywords_for_text(connection, id)

        return item.keywords

    def queue_final_save(self, metadata):
        db.final_updater.execution_fn = data.update_text
        db.final_updater.enqueue(metadata['id'], metadata)

    def delete_item_at_postion(self, position):
        """Delete item at @position in model

        @self: DraftListStore model
        @position: integer, position at which the item to be deleted is located
        """
        item = self.get_item(position)
        id = item.db_id
        hash_id = item.hash_id
        parent_hashes = item.parent_list
        item.in_trash = True

        self.remove(position)
        file.trash_file(hash_id, parent_hashes)

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

    def get_data_for_position(self, position):
        item = self.get_item(position)
        return item.to_dict()

    def get_position_for_id(self, text_id):
        length = self.get_n_items()
        for i in range(length):
            item = self.get_item(i)
            if item.db_id == text_id:
                return i

        return None

    def get_latest_modified_position(self):
        length = self.get_n_items()

        # move to utils
        from datetime import datetime
        latest_modified = None
        latest_position = None

        for i in range(length):
            item = self.get_item(i)
            text_data = item.to_dict()
            text_last_modified = datetime.strptime(text_data['last_modified'],
                                                   '%Y-%m-%dT%H:%M:%S.%f')
            if not latest_modified or text_last_modified > latest_modified:
                latest_modified = text_last_modified
                latest_position = i

        return latest_position
