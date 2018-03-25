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

from gi.repository import Gtk, GObject


class CollectionClassType(Enum):
    ALL = 0
    RECENT = 1


class Column(object):
    NAME = 0
    TYPE = 1


class DraftCollectionListStore(Gtk.ListStore):
    """The model for representing useful collection classes."""
    _all_class_row_values = [
        _("All Texts"),
        CollectionClassType.ALL
    ]
    _recent_class_row_values = [
        _("Recent"),
        CollectionClassType.RECENT
    ]

    def __repr__(self):
        return '<DraftCollectionListStore>'

    def __init__(self):
        Gtk.ListStore.__init__(
            self,
            GObject.TYPE_STRING,        # name of class
            GObject.TYPE_PYOBJECT       # type of class
        )
        self._append_classes()

    def _append_classes(self):
        """Append classes to the model"""
        self.append(self._all_class_row_values)
        self.append(self._recent_class_row_values)
