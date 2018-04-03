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

    def get_data_for_position(self, position):
        """Return a dict of tag data for the given position"""
        item = self.get_item(position)
        return item.to_dict()
