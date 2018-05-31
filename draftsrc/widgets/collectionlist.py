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
from gi.repository import Gtk, GObject, Pango

from draftsrc.models.collectionliststore import DraftCollectionListStore, Column


class DraftCollectionList(Gtk.TreeView):
    """A list view for providing different classes of groups and text, such as
    user's collection, trashed items, recently modified items, etc.
    """
    __gtype_name__ = 'DraftCollectionList'

    __gsignals__ = {
        'class-selected': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           (GObject.TYPE_PYOBJECT,)),
    }

    def __repr__(self):
        return '<DraftCollectionList>'

    def __init__(self):
        Gtk.TreeView.__init__(self, DraftCollectionListStore())
        ctx = self.get_style_context()
        ctx.add_class('draft-treeview')

        self.selection = self.get_selection()
        self.selection.connect('changed', self._on_selection_changed)

        self.set_headers_visible(False)
        self.set_enable_search(False)
        self._populate()

    def _populate(self):
        """Set up cell renderer and column for the view"""
        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        renderer.set_fixed_size(-1, 28)
        column = Gtk.TreeViewColumn(_("Library"), renderer, text=Column.NAME)
        self.title = column
        self.append_column(column)
        self.title.set_expand(True)

    def _on_selection_changed(self, selection):
        """Handle selection changed signal and then emit 'class-selected' signal"""
        model, treeiter = self.selection.get_selected()

        if not (model and treeiter):
            return

        collection_class_type = model[treeiter][Column.TYPE]
        self.emit('class-selected', collection_class_type)

    def should_move_down(self):
        """Whether selection is the end and should move to next widget."""
        model, treeiter = self.selection.get_selected()
        return model.get_path(treeiter) == model[-1].path

    def focus_bottom_level(self):
        """Selects and focuses on the bottom-most visible node."""
        model = self.get_model()
        last_path = model[-1].path
        self.set_cursor(last_path, None, False)
