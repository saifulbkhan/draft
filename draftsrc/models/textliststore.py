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


class TextListType(object):
    GROUP_TEXTS = 0
    ALL_TEXTS = 1
    RECENT_TEXTS = 2
    RESULT_TEXTS = 3


class TextRowData(GObject.Object):
    """Represents one entry in list of texts"""
    __gtype_name__ = 'TextRowData'

    def __init__(self, title='', tags=[], last_modified='', db_id=None,
                 hash_id='', in_trash=False, parent_id=None, parent_list=[],
                 markup=None, subtitle=None, word_goal=None,
                 last_edit_position=None, misc=None):
        super().__init__()
        self.title = title
        self.tags = tags
        self.last_modified = last_modified
        self.db_id = db_id
        self.hash_id = hash_id
        self.in_trash = in_trash
        self.parent_id = parent_id
        self.parent_list = parent_list
        self.markup = markup
        self.subtitle = subtitle
        self.word_goal = word_goal
        self.last_edit_position = last_edit_position
        self.misc = misc

    @classmethod
    def from_dict(cls, data_dict):
        title = data_dict['title']
        tags = data_dict['tags']
        last_modified = data_dict['last_modified']
        db_id = data_dict['id']
        hash_id = data_dict['hash_id']
        in_trash = bool(data_dict['in_trash'])
        parent_id = data_dict['parent_id']
        parent_list = data_dict['parents']
        markup = data_dict['markup']
        subtitle = data_dict['subtitle']

        word_goal = 0
        if data_dict['word_goal']:
            word_goal = int(data_dict['word_goal'])

        last_edit_position = 0
        if data_dict['last_edit_position']:
            last_edit_position = int(data_dict['last_edit_position'])

        misc = data_dict.get('misc')

        row = cls(title, tags, last_modified, db_id, hash_id, in_trash,
                  parent_id, parent_list, markup, subtitle, word_goal,
                  last_edit_position, misc)
        return row

    def to_dict(self):
        return {
            'title': self.title,
            'tags': self.tags,
            'last_modified': self.last_modified,
            'id': self.db_id,
            'hash_id': self.hash_id,
            'in_trash': int(self.in_trash),
            'parent_id': self.parent_id,
            'parent_list': self.parent_list,
            'markup': self.markup,
            'subtitle': self.subtitle,
            'word_goal': int(self.word_goal),
            'last_edit_position': int(self.last_edit_position),
            'misc': self.misc
        }

    def update_from_dict(self, data_dict):
        self.title = data_dict['title']
        self.tags = data_dict['tags']
        self.last_modified = data_dict['last_modified']
        self.db_id = data_dict['id']
        self.hash_id = data_dict['hash_id']
        self.in_trash = bool(data_dict['in_trash'])
        self.parent_id = data_dict['parent_id']
        self.parent_list = data_dict['parent_list']
        self.markup = data_dict['markup']
        self.subtitle = data_dict['subtitle']

        self.word_goal = 0
        if data_dict['word_goal']:
            self.word_goal = int(data_dict['word_goal'])

        self.last_edit_position = 0
        if data_dict['last_edit_position']:
            self.last_edit_position = int(data_dict['last_edit_position'])

        self.misc = data_dict.get('misc')


class DraftTextListStore(Gio.ListStore):
    """Model for a list of texts (only) from one particular text group"""

    def __repr__(self):
        return '<DraftListStore>'

    def __init__(self, list_type, parent_group=None, results={}, trashed=False):
        """Initialises a new DraftListStore of given type. For some types extra
        information like the parent group or tag need to be provided as well.

        @parent_group: dict, storing parent group details
        @tag: dict, sotring details of tag
        @trashed: boolean, whether the model should show trashed texts only
        """
        Gio.ListStore.__init__(self, item_type=TextRowData.__gtype__)
        self._list_type = list_type
        self.trashed_texts_only = trashed

        if self._list_type == TextListType.GROUP_TEXTS:
            assert parent_group is not None
            self._parent_group = parent_group
        elif self._list_type == TextListType.RESULT_TEXTS:
            assert len(results) > 0
            self._results = results

        self._load_texts()

    def _load_texts(self):
        """Asks db to fetch the set of texts in @parent_group"""
        self.remove_all()
        with db.connect() as connection:
            load_fn = None
            kwargs = {}
            load_orphan_trash = False
            if self._list_type == TextListType.GROUP_TEXTS:
                if self._parent_group['id']:
                    load_fn = data.texts_in_group
                    kwargs = {
                        'conn': connection,
                        'group_id': self._parent_group['id']
                    }
                else:
                    load_fn = data.texts_not_in_groups
                    kwargs = {'conn': connection}
                    if self.trashed_texts_only:
                        load_orphan_trash = True
            elif self._list_type == TextListType.RECENT_TEXTS:
                load_fn = data.texts_recently_modified
                kwargs = {'conn': connection}
            elif self._list_type == TextListType.RESULT_TEXTS:

                def texts_in_results(conn, results):
                    for text_id in results:
                        text_id = int(text_id)
                        yield data.text_for_id(conn, text_id)

                load_fn = texts_in_results
                kwargs = {
                    'conn': connection,
                    'results': self._results
                }
            else:
                load_fn = data.fetch_texts
                kwargs = {'conn': connection}

            for text in load_fn(**kwargs):
                row = self._row_data_for_text(text)
                if self.trashed_texts_only and row.in_trash:
                    self.append(row)
                elif not self.trashed_texts_only and not row.in_trash:
                    self.append(row)
            if load_orphan_trash:
                for text in data.texts_in_trash_but_not_parent(connection):
                    row = self._row_data_for_text(text)
                    self.append(row)

    def _row_data_for_text(self, text_metadata):
        """Create TextRowData for one text document. Expects a dict of metadata"""
        if self._list_type == TextListType.RESULT_TEXTS:
            text_id = str(text_metadata['id'])
            text_metadata['misc'] = self._results[text_id]
        row_data = TextRowData.from_dict(text_metadata)
        return row_data

    def new_text_request(self):
        """Request for a new text

        @self: DraftListStore model
        """
        if self._parent_group is None:
            return

        with db.connect() as connection:
            text_id = data.create_text(connection,
                                       _("Untitled"),
                                       self._parent_group['id'])
            text = data.text_for_id(connection, text_id)
            text_row = self._row_data_for_text(text)
            return self.append(text_row)

    def prepare_for_edit(self, positions, switch_view, load_file):
        """Prepare text at @position in @self to be edited.

        @self: DraftListStore model
        @positions: list, positions at which the item to be edited is located
                    in the model
        @switch_view: method, called to check if a new editor buffer is needed
        @load_file: method, passed on to `file.read_file_contents` function
        """
        items = [self.get_item(position) for position in positions]
        if None in items:
            return

        buffers = switch_view([item.to_dict() for item in items])
        if not buffers:
            return

        for item in items:
            if item.db_id in buffers:
                hash_id = item.hash_id
                parent_hashes = list(item.parent_list)
                in_trash = self.trashed_texts_only
                file.read_file_contents(hash_id,
                                        parent_hashes,
                                        buffers.get(item.db_id),
                                        load_file,
                                        in_trash)

    def update_model_item_for_position(self, position, metadata):
        """Only updates the model entry (at @position) with given metadata. No
        updates are made to the db."""
        item = self.get_item(position)
        item.update_from_dict(metadata)

    def set_prop_for_position(self, position, prop, value):
        """Set property @prop for item at @position to @value

        @self: DraftListStore model
        @position: integer, position at which item is located
        @prop: string, property to be set
        @value: obj, value to be assigned to @prop
        """
        if prop == 'tags':
            return self.set_tags_for_position(position, value)
        elif prop == 'parent_id':
            return self.set_parent_for_position(position, value)

        item = self.get_item(position)
        id = item.db_id
        setattr(item, prop, value)
        item.last_modified = db.get_datetime()
        # TODO: 'notify' view that a prop for an item has changed

        db.async_text_updater.enqueue(id, item.to_dict())

    def set_parent_for_position(self, position, parent):
        """Set the parent id for text at given position and move the text to
        the corresponding folder"""
        item = self.get_item(position)
        item.parent_id = parent
        item.last_modified = db.get_datetime()
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

        self.dequeue_final_save(id)

        if self._parent_group and parent != self._parent_group:
            self.remove(position)
        return item.db_id

    def set_tags_for_position(self, position, tags):
        """Set the tags for the item at given position

        @self: DraftListStore model
        @position: integer, position at which  item is located
        @tags: list, the collection of strings as tags for the item
        """
        item = self.get_item(position)
        item.tags = tags
        item.last_modified = db.get_datetime()
        id = item.db_id

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

            # update tags after, they have been updated in db
            item.tags = data.fetch_tags_for_text(connection, id)

        self.dequeue_final_save(id)

        return item.tags

    def queue_save(self, metadata):
        text_id = metadata['id']
        db.final_text_updater.remove_if_exists(text_id)
        db.async_text_updater.enqueue(text_id, metadata)

    def queue_final_save(self, metadata):
        db.final_text_updater.enqueue(metadata['id'], metadata)

    def dequeue_final_save(self, id):
        db.final_text_updater.remove_if_exists(id)

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
        item.last_modified = db.get_datetime()

        self.remove(position)
        file.trash_file(hash_id, parent_hashes)

        with db.connect() as connection:
            self.queue_save(item.to_dict())

        self.dequeue_final_save(id)

    def restore_item_at_position(self, position):
        """Restore an item from trash, assuming its there already"""
        item = self.get_item(position)
        if not item.in_trash:
            return

        id = item.db_id
        hash_id = item.hash_id
        parent_hashes = item.parent_list
        item.in_trash = False
        item.last_modified = db.get_datetime()

        self.remove(position)

        with db.connect() as connection:
            if item.parent_id:
                group = data.group_for_id(connection, item.parent_id)
                if group['in_trash']:
                    item.parent_id = None
                    parent_hashes = []

            file.trash_file(hash_id, parent_hashes, untrash=True)
            data.update_text(connection, id, item.to_dict())

        self.dequeue_final_save(id)

    def delete_item_at_postion_permanently(self, position):
        """Delete an item from trash permanently"""
        item = self.get_item(position)
        if not item.in_trash:
            return

        id = item.db_id
        hash_id = item.hash_id

        self.remove(position)
        file.delete_file_permanently(hash_id)
        db.async_text_deleter.enqueue(id, None)

        self.dequeue_final_save(id)

    def get_data_for_position(self, position, parent_group=False):
        """Obtain a dictionary of metadata for the given position. If the
        optional argument @parent_group is supplied `True`, then the group is
        returned as a dictionary as well."""
        item = self.get_item(position)
        if parent_group:
            if item.parent_id:
                with db.connect() as connection:
                    group = data.group_for_id(connection, item.parent_id)
                    return item.to_dict(), group
            else:
                return item.to_dict(), None
        return item.to_dict()

    def get_position_for_id_in_range(self, text_id, pos_range):
        for i in pos_range:
            item = self.get_item(i)
            if item.db_id == text_id:
                return i

        return None

    def get_position_for_id(self, text_id):
        length = self.get_n_items()
        return self.get_position_for_id_in_range(text_id,
                                                  range(self.get_n_items()))

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

    def get_model_attributes(self):
        """Obtain details about this model."""
        group = None
        if self._list_type == TextListType.GROUP_TEXTS:
            group = self._parent_group

        return self._list_type, group, self.trashed_texts_only
