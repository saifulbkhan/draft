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

from gi.repository import Gtk, GObject, Gio

from draftsrc import db
from draftsrc.db import data


class DraftTagListStore(Gio.ListStore):
    """The model for representing all the tags being used by texts"""

    class TagData(GObject.Object):
        """Data for one tag"""
        __gtype_name__ = 'TagData'

        label = ''

        def from_dict(self, data_dict):
            self.label = data_dict['keyword']

        def to_dict(self):
            return {
                'keyword': self.label
            }

    def __repr__(self):
        return '<DraftTagListStore>'

    def __init__(self):
        Gio.ListStore.__init__(self, item_type=self.TagData.__gtype__)
        self._load_tags()

    def _load_tags(self):
        """Connects to db and loads tags tagged to at least one text."""
        with db.connect() as connection:
            for tag in data.tags_with_at_least_one_text(connection):
                row = self._row_for_tag(tag)
                self.append(row)

    def _row_for_tag(self, tag):
        """Return a TagData element for given tag values"""
        row = self.TagData()
        row.from_dict(tag)
        return row

    def _get_tags_and_positions(self):
        """Return a dict of tags and their current positions in the model"""
        num_items = self.get_n_items()
        tags_and_positions = {}
        for index in range(num_items):
            tag = self.get_item(index)
            tags_and_positions[tag.label] = index
        return tags_and_positions

    def get_data_for_position(self, position):
        """Return a dict of tag data for the given position"""
        item = self.get_item(position)
        return item.to_dict()

    def get_position_for_tag(self, label):
        """Return the position for given label if founf in the model, -1
        otherwise"""
        num_items = self.get_n_items()
        for index in range(num_items):
            tag = self.get_item(index)
            if tag.label == label:
                return index
        return -1

    def update(self, tags):
        """If any tag in @tags are absent from model, add it. If any tags in
        model are not in tag, re-assess their presence."""
        current_tags_and_position = self._get_tags_and_positions()
        num_items = len(current_tags_and_position)
        current_tags = {label for label in current_tags_and_position.keys()}
        tags = set(tags)

        absent_tags = tags - current_tags
        tags_to_reassess = current_tags - tags

        with db.connect() as connection:
            for label in absent_tags:
                tag = data.tag_with_label(connection, label)
                row = self._row_for_tag(tag)
                self.append(row)

            for label in tags_to_reassess:
                num_items_with_tag = data.count_texts_with_tag(connection, label)
                if num_items_with_tag == 0:
                    self.remove(current_tags_and_position[label])
