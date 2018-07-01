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

    def __init__(self, title='', tags=[], last_modified='', id=None,
                 hash_id='', in_trash=False, parent_id=None, parents=[],
                 markup=None, subtitle=None, word_goal=None,
                 last_edit_position=None, misc=None):
        """Initialize a TextRowData object representing a single sheet with
        given attributes

        :param title: A string title for the sheet
        :param tags: A list of string labels tagged to the sheet
        :param last_modified: Date-time when sheet was last modified (ISO8601
                              formatted)
        :param id: Valid DB ID from the "text" table, for this sheet
        :param hash_id: A unique hash, to be used as filename for sheet's
                        contents
        :param in_trash: Boolean denoting whether sheet has been trashed or not
        :param parent_id: Valid DB ID from the "group" table, denoting parent
                          association
        :param parents: A list unique hashes, to locate the containing
                            folder of sheet
        :param markup: A string denoting the type of markup used by sheet
                       contents
        :param subtitle: A subtitle string for the sheet
        :param word_goal: Writing goal in terms of word count
        :param last_edit_position: The position offset of the cursor when last
                                   viewed
        :param misc: Any other miscellaneous details
        """
        super().__init__()
        self.title = title
        self.tags = tags
        self.last_modified = last_modified
        self.id = id
        self.hash_id = hash_id
        self.in_trash = in_trash
        self.parent_id = parent_id
        self.parents = parents
        self.markup = markup
        self.subtitle = subtitle
        self.word_goal = word_goal
        self.last_edit_position = last_edit_position
        self.misc = misc

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    @classmethod
    def from_dict(cls, data_dict):
        """Create an instance of TextRowData using the given metadata

        :param data_dict: A dictionary of metdata for a sheet

        :returns: A row data object that can be used as an entry within
                  DraftTextListStore
        :rtype: TextRowData
        """
        row = cls()
        cls.update_from_dict(row, data_dict)
        return row

    def to_dict(self):
        """Convert ``self`` to a dictionary of sheet attributes

        :returns: Key-value mapping for useful sheet metadata
        :rtype: dict
        """
        return {
            'title': self.title,
            'tags': self.tags,
            'last_modified': self.last_modified,
            'id': self.id,
            'hash_id': self.hash_id,
            'in_trash': int(self.in_trash),
            'parent_id': self.parent_id,
            'parents': self.parents,
            'markup': self.markup,
            'subtitle': self.subtitle,
            'word_goal': int(self.word_goal),
            'last_edit_position': int(self.last_edit_position),
            'misc': self.misc
        }

    def update_from_dict(self, data_dict):
        """Update ``self`` attributes from the given metadata

        :param data_dict: A dictionary of sheet metadata
        """
        self.title = data_dict['title']
        self.tags = data_dict['tags']
        self.last_modified = data_dict['last_modified']
        self.id = data_dict['id']
        self.hash_id = data_dict['hash_id']
        self.in_trash = bool(data_dict['in_trash'])
        self.parent_id = data_dict['parent_id']
        self.parents = data_dict['parents']
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

        :param parent_group: A dict storing parent group details
        :param tag: A dict storing details of tag
        :param trashed: Whether the model should show trashed texts only
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
        """Asks db to fetch the set of texts according to init conditions"""
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
        """Create TextRowData for one text document

        :param text_metadata: A dict of metadata"""
        if self._list_type == TextListType.RESULT_TEXTS:
            text_id = str(text_metadata['id'])
            text_metadata['misc'] = self._results[text_id]
        row_data = TextRowData.from_dict(text_metadata)
        return row_data

    def new_text_request(self):
        """Request for a new text"""
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
        """Prepare text at ``position`` in ``self`` to be edited

        :param self: DraftListStore model
        :param positions: A list of positions at which the items to be edited
                          are located in the model
        :param switch_view: A method called to check if a new editor buffer is
                            needed
        :param load_file: A method passed on to ``file.read_file_contents``
                          function - post-load callback
        """
        items = [self.get_item(position) for position in positions]
        if None in items:
            return

        buffers = switch_view(items)
        if not buffers:
            return

        for item in items:
            if item.id in buffers:
                hash_id = item.hash_id
                parent_hashes = list(item.parents)
                in_trash = self.trashed_texts_only
                file.read_file_contents(hash_id,
                                        parent_hashes,
                                        buffers.get(item.id),
                                        load_file,
                                        in_trash)

    def set_prop_for_position(self, position, prop, value):
        """Set a property for given ``position`` to a new value

        The database is also updated reflecting this change

        :param position: A non-negative integer position of item to be changed
        :param prop: Name of property to update the value
        :param value: The value to be assigned to ``prop``
        """
        if prop == 'tags':
            return self.set_tags_for_position(position, value)
        elif prop == 'parent_id':
            return self.set_parent_for_position(position, value)

        item = self.get_item(position)
        id = item.id
        setattr(item, prop, value)
        item.last_modified = db.get_datetime()
        # TODO: 'notify' view that a prop for an item has changed

        db.async_text_updater.enqueue(id, item.to_dict())

    def set_parent_for_position(self, position, parent):
        """Set the parent id for text at given position and move the text to
        the corresponding folder

        :param position: A non-negative integer position of item to be changed
        :param parent: A valid database ID for a group, denoting parent
                       association
        """
        item = self.get_item(position)
        self.set_parent_for_items(item, parent)
        if self._parent_group and parent != self._parent_group:
            self.remove(position)
        return item.id

    def set_parent_for_items(self, items, parent):
        """A method to ease setting parent id for a batch of items

        :param items: A list of row data items or a single item, to be moved
        :param parent: A valid database ID for a group, denoting parent
                       association
        """
        if not isinstance(items, list):
            items = [items]

        with db.connect() as connection:
            for item in items:
                item.parent_id = parent
                item.last_modified = db.get_datetime()
                id = item.id
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

                file.move_file(text_file_name,
                               text_file_parents,
                               group_dir_parents)

                item.parents = group_dir_parents
                data.update_text(connection, id, item.to_dict())
                self.dequeue_final_save(id)

    def set_tags_for_position(self, position, tags):
        """Set the tags for the item at given position

        :param position: integer position at which item is located
        :parm tags: the collection (list) of strings as tags for the item
        """
        item = self.get_item(position)
        item.tags = tags
        item.last_modified = db.get_datetime()
        id = item.id

        with db.connect() as connection:
            data.update_text(connection, id, item.to_dict())

            # update tags after, they have been updated in db
            item.tags = data.fetch_tags_for_text(connection, id)

        self.dequeue_final_save(id)

        return item.tags

    def queue_save(self, text_data):
        """Queue given metadata to be updated in DB, as soon as a connection is
        available for the operation

        :param text_data: A TextRowData object associated with a text
        """
        text_id = text_data.id
        db.final_text_updater.remove_if_exists(text_id)
        db.async_text_updater.enqueue(text_id, text_data.to_dict())

    def queue_final_save(self, text_data):
        """Queue given metadata to be updated in DB, but only done when the app
        quits

        :param text_data: A TextRowData object associated with a text
        """
        db.final_text_updater.enqueue(text_data.id, text_data.to_dict())

    def dequeue_final_save(self, id):
        """Dequeue any metadata update that was meant to be done when app quits

        :param id: A valid sheet ID, present as a key in update queue dict
        """
        db.final_text_updater.remove_if_exists(id)

    def delete_item_at_postion(self, position):
        """Delete item at ``position`` in model

        :param position: integer position at which item is located
        """
        item = self.get_item(position)
        id = item.id
        hash_id = item.hash_id
        parent_hashes = item.parents
        item.in_trash = True
        item.last_modified = db.get_datetime()

        self.remove(position)
        file.trash_file(hash_id, parent_hashes)

        with db.connect() as connection:
            self.queue_save(item)

        self.dequeue_final_save(id)

    def restore_item_at_position(self, position):
        """Restore an item from trash, assuming its there already

        :param position: integer position at which item is located
        """
        item = self.get_item(position)
        if not item.in_trash:
            return

        id = item.id
        hash_id = item.hash_id
        parent_hashes = item.parents
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
        """Delete an item from trash permanently

        :param position: integer position at which item is located
        """
        item = self.get_item(position)
        if not item.in_trash:
            return

        id = item.id
        hash_id = item.hash_id

        self.remove(position)
        file.delete_file_permanently(hash_id)
        db.async_text_deleter.enqueue(id, None)

        self.dequeue_final_save(id)

    def get_parent_for_position(self, position):
        """Obtain parent group data for the given position

        :param position: integer position at which item is located

        :returns: group metadata as a dictionary
        :rtype: dict
        """
        item = self.get_item(position)
        if item.parent_id:
            with db.connect() as connection:
                group = data.group_for_id(connection, item.parent_id)
                return group
        return None

    def get_position_for_id_in_range(self, text_id, pos_range):
        """For a given set of item positions, check if the sheet for given
        ``text_id`` is present within and return its position

        :param text_id: A valid DB ID for sheet that would be checked for
        :param pos_range: A list of positions to be checked

        :returns: The position of sheet with matching DB ID if found, otherwise
                  None
        :rtype: int or None
        """
        for i in pos_range:
            item = self.get_item(i)
            if item.id == text_id:
                return i

        return None

    def get_position_for_id(self, text_id):
        """Obtian the position of sheet within the list using its DB ID

        :param text_id: A valid DB ID of the sheet to be found

        :returns: A position within the list if ``text_id`` is found, otherwise
                  None
        :rtype: int or None
        """
        length = self.get_n_items()
        return self.get_position_for_id_in_range(text_id,
                                                 range(self.get_n_items()))

    def get_latest_modified_position(self):
        """Get the position of the last modified sheet

        :returns: The position of a sheet within the model
        :rtype: int
        """
        length = self.get_n_items()

        # move to utils
        from datetime import datetime
        latest_modified = None
        latest_position = None

        for i in range(length):
            item = self.get_item(i)
            text_last_modified = datetime.strptime(item.last_modified,
                                                   '%Y-%m-%dT%H:%M:%S.%f')
            if not latest_modified or text_last_modified > latest_modified:
                latest_modified = text_last_modified
                latest_position = i

        return latest_position

    def get_model_attributes(self):
        """Obtain details about this model

        :returns: A tuple containing list type, parent group ID and trash status
        :rtype: (TextListType, int or None, bool)
        """
        group = None
        if self._list_type == TextListType.GROUP_TEXTS:
            group = self._parent_group

        return self._list_type, group, self.trashed_texts_only
