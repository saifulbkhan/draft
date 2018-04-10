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

from enum import Enum
from gettext import gettext as _

from gi.repository import GObject, Gtk

from draftsrc import file, db
from draftsrc.db import data


class Column(object):
    NAME = 0
    CREATED = 1
    LAST_MODIFIED = 2
    IN_TRASH = 3
    ID = 4
    PARENT_ID = 5


class GroupTreeType(Enum):
    COLLECTION_GROUPS = 0
    TRASHED_GROUPS = 2


class DraftGroupTreeStore(Gtk.TreeStore):
    """Model for storing metadata related to heirarchical group structures"""
    _top_level_iter = None

    def __repr__(self):
        return '<DraftTreeStore>'

    def __init__(self, tree_type, top_row_name):
        Gtk.TreeStore.__init__(
            self,
            GObject.TYPE_STRING,        # name of group
            GObject.TYPE_STRING,        # date created
            GObject.TYPE_STRING,        # date last modified
            GObject.TYPE_BOOLEAN,       # whether in trash or not
            GObject.TYPE_INT,           # id of the group
            GObject.TYPE_PYOBJECT       # id of the parent group, can be null
        )
        self.tree_type = tree_type
        self._append_top_level_row(top_row_name)
        self._load_data()

    def _append_top_level_row(self, top_row_name):
        top_level_group = self._dict_for_top_level_row(top_row_name)
        self._top_level_iter = self._append_group(top_level_group)

    def _load_data(self):
        """Load group data into tree model, according to groupt tree type"""
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
        if self.tree_type != GroupTreeType.TRASHED_GROUPS and group['in_trash']:
            return

        if not treeiter:
            treeiter = self._top_level_iter

        if ((self.tree_type == GroupTreeType.TRASHED_GROUPS
                and group['in_trash'])
                or (self.tree_type != GroupTreeType.TRASHED_GROUPS
                and not group['in_trash'])):
            treeiter = self._append_group(group, treeiter)

        for child_group in data.groups_in_group(connection, group['id']):
            self._append_group_and_children(connection, child_group, treeiter)

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

    def _update_group(self, treeiter, group):
        """Update the row at @treeiter with values from @group"""
        cols = ['name', 'created', 'last_modified', 'in_trash', 'id', 'parent_id']
        for col in cols:
            col_id = col.upper()
            self[treeiter][getattr(Column, col_id)] = group[col]

    def get_group_for_iter(self, treeiter):
        """For the given @treeiter return a valid dict with metadata values"""
        if self._iter_is_top_level(treeiter):
            return self._dict_for_top_level_row()

        return self._dict_for_row(treeiter)

    def _dict_for_top_level_row(self, row_name=None):
        if not row_name:
            row_name = self[self._top_level_iter][Column.NAME]

        in_trash = False
        if self.tree_type == GroupTreeType.TRASHED_GROUPS:
            in_trash = True

        return {
            'name': row_name,
            'created': db.get_datetime(),
            'last_modified': None,
            'in_trash': in_trash,
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

    def _dict_for_decoy_group(self, parent_id):
        return {
            'name': _("New Group"),
            'created': None,
            'last_modified': None,
            'in_trash': False,
            'id': None,
            'parent_id': parent_id
        }

    def _iter_is_top_level(self, treeiter):
        path = self.get_path(treeiter)
        top_level_path = self.get_path(self._top_level_iter)

        if path == top_level_path:
            return True

        return False

    def create_decoy_group(self, parent_iter=None):
        """Create a new text group and append it to the @parent_iter node"""
        parent_id = None
        if parent_iter and not self._iter_is_top_level(parent_iter):
            parent_id = self[parent_iter][Column.ID]

        group = self._dict_for_decoy_group(parent_id)
        return self._append_group(group, parent_iter)

    def finalize_group_creation(self, treeiter, name):
        """Finalize creation of the decoy group at @treeiter with the new @name"""
        parent_id = self[treeiter][Column.PARENT_ID]
        with db.connect() as connection:
            group_id = data.create_group(connection, name, parent_id)
            group = data.group_for_id(connection, group_id)
            file.create_dir(group['hash_id'], group['parents'])
            self._update_group(treeiter, group)
            return group

    def set_prop_for_iter(self, treeiter, prop, value):
        """Set the property @prop to @value for the row given by @treeiter. This
        method does not make changes to the model if the parent id is changed.
        Instead, use `move_to_group` method which along with making necessary
        changed, will also automatically call this method for update to db."""
        if self._iter_is_top_level(treeiter):
            return

        assert prop in ['name', 'last_modified', 'in_trash', 'parent_id']

        old_parent = self[treeiter][Column.PARENT_ID]
        new_parent = self[treeiter][Column.PARENT_ID]
        trashed = False
        if prop == 'name':
            self[treeiter][Column.NAME] = value
        elif prop == 'last_modified':
            self[treeiter][Column.LAST_MODIFIED] = value
        elif prop == 'in_trash':
            self[treeiter][Column.IN_TRASH] = trashed = value
        elif prop == 'parent_id':
            self[treeiter][Column.PARENT_ID] = new_parent = value

        values = self._dict_for_row(treeiter)
        group_id = values['id']
        with db.connect() as connection:
            if old_parent != new_parent:
                group = data.group_for_id(connection, group_id)
                group_dir_name = group['hash_id']
                group_dir_parents = group['parents']

                new_parent_dir_parents = []
                if new_parent:
                    new_parent_group = data.group_for_id(connection, new_parent)
                    new_parent_dir_name = new_parent_group['hash_id']
                    new_parent_dir_parents = new_parent_group['parents']
                    new_parent_dir_parents.append(new_parent_dir_name)

                    # update the new parent's last modified status
                    data.update_group(connection, new_parent, new_parent_group)

                if old_parent:
                    # update the old parent's last modified status
                    old_parent_group = data.group_for_id(connection, old_parent)
                    data.update_group(connection, old_parent, old_parent_group)

                file.move_file(group_dir_name,
                               group_dir_parents,
                               new_parent_dir_parents)

            if trashed and self.tree_type == GroupTreeType.COLLECTION_GROUPS:
                group = data.group_for_id(connection, group_id)
                texts_to_be_trashed = self._all_texts_in_group(connection,
                                                               group['id'],
                                                               in_trash=False)
                for text in texts_to_be_trashed:
                    parent_list = texts_to_be_trashed[text]
                    file.trash_file(text, parent_list)

            if not trashed and self.tree_type == GroupTreeType.TRASHED_GROUPS:
                group = data.group_for_id(connection, group_id)
                if group['parent_id'] is not None:
                    parent_group = data.group_for_id(connection, group['parent_id'])
                    # if a group is being restored whose parents are still in
                    # trash, then make this group exist on its own in the main
                    # collection i.e., with no parents.
                    if parent_group['in_trash']:
                        values['parent_id'] = None
                texts_to_be_restored = self._all_texts_in_group(connection,
                                                                group['id'],
                                                                in_trash=True)
                for text in texts_to_be_restored:
                    parent_list = texts_to_be_restored[text]
                    # if group's parent is being set to NULL, then restore the
                    # files within to correct locations accordingly
                    if not values['parent_id']:
                        parent_list = parent_list[parent_list.index(group['hash_id']):]
                    file.trash_file(text, parent_list, untrash=True)

            data.update_group(connection, group_id, values)

        if trashed and self.tree_type != GroupTreeType.TRASHED_GROUPS:
            self.remove(treeiter)

        if not trashed and self.tree_type == GroupTreeType.TRASHED_GROUPS:
            self.remove(treeiter)

    def _all_texts_in_group(self, connection, group_id, in_trash):
        texts_in_group = {}

        def append_texts_in_group(id):
            for text in data.texts_in_group(connection, id):
                if text['in_trash'] == in_trash:
                    texts_in_group[text['hash_id']] = text['parents']
            for group in data.groups_in_group(connection, id):
                append_texts_in_group(group['id'])

        append_texts_in_group(group_id)
        return texts_in_group

    def move_to_group(self, child_iter, parent_iter):
        """Move group at @child_iter to group @parent_iter and set this parent
        in db as well"""
        if self.is_ancestor(child_iter, parent_iter):
            return None

        new_parent_id = self[parent_iter][Column.ID]
        if self._iter_is_top_level(parent_iter):
            new_parent_id = None

        self.set_prop_for_iter(child_iter, 'parent_id', new_parent_id)
        treeiter = self._recursive_move_group(child_iter, parent_iter)
        self.remove(child_iter)
        return treeiter

    def _recursive_move_group(self, child_iter, parent_iter):
        """Recursively move one group to another in the model. Note the group
        being moved must still be removed from the model to avoid duplication.
        Also, the changes are not reflected in the database. Therefore the
        `move_to_group` should be used instead of this; this is basically a
        helper function."""
        group = self.get_group_for_iter(child_iter)
        treeiter = self._append_group(group, parent_iter)
        if self.iter_has_child(child_iter):
            grand_child_iter = self.iter_children(child_iter)
            while grand_child_iter is not None:
                self._recursive_move_group(grand_child_iter, treeiter)
                grand_child_iter = self.iter_next(grand_child_iter)

        return treeiter

    def permanently_delete_group_at_iter(self, treeiter):
        """Remove the row @treeiter from model and delete the group for this
        entry from the DB as well, unless its the root node."""
        values = self.get_group_for_iter(treeiter)
        group_id = values['id']
        texts_to_be_deleted = []
        with db.connect() as connection:
            texts_to_be_deleted = self._all_texts_in_group(connection,
                                                           group_id,
                                                           in_trash=True)
        for text_name in texts_to_be_deleted:
            file.delete_file_permanently(text_name)

        if group_id is not None:
            db.async_group_deleter.enqueue(group_id, None)

        if not self._iter_is_top_level(treeiter):
            self.remove(treeiter)

    def count_groups_for_iter(self, treeiter):
        """Count the number of groups contained within group at @treeiter"""
        group = self.get_group_for_iter(treeiter)
        group_id = group['id']
        in_trash = group['in_trash']

        with db.connect() as connection:
            if self._iter_is_top_level(treeiter) and in_trash:
                return self.iter_n_children(self._top_level_iter)
            return data.count_groups(connection, group_id, in_trash)

    def count_texts_for_iter(self, treeiter):
        """Count the number of texts contained within group at @treeiter"""
        group = self.get_group_for_iter(treeiter)
        group_id = group['id']
        in_trash = group['in_trash']

        count = 0
        with db.connect() as connection:
            count += data.count_texts(connection, group_id, in_trash)
            if self._iter_is_top_level(treeiter) and in_trash:
                count += data.count_texts_in_trash_but_not_parent(connection)

        return count
