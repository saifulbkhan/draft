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

from gi.repository import Gtk, GLib
from notosrc.treestore import TreeStore

class NotesView(Gtk.Bin):
    sidebar_width = 300
    def __repr__(self):
        return '<NotesView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/notesview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        noteslist = self.builder.get_object('noteslist')
        listview = self.builder.get_object('listview')

        self.add(noteslist)
        self.view = ListView(self.parent_window)
        listview.add(self.view)

        self.search_bar = self.builder.get_object('search_bar')
        self.search_entry = self.builder.get_object('search_entry')

    def search_toggled(self):
        if self.search_bar.get_search_mode():
            self.search_bar.set_search_mode(False)
            self.search_entry.set_text("")
        else:
            self.search_bar.set_search_mode(True)
            self.search_entry.grab_focus()


class ListView(Gtk.TreeView):

    def __repr__(self):
        return '<ListView>'

    def __init__(self, window):
        Gtk.TreeView.__init__(self, TreeStore())
        self.model = self.get_model()
        self.main_window = window

        self.selection = self.get_selection()
        self.selection.connect('changed', self._on_selection_changed)

        self._populate()
        self.set_headers_visible(False)

    def _populate(self):
        for i, title in enumerate([_("Title"), "", _("Last Edited")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.append_column(column)

    def _on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if not self.main_window.is_showing_content():
            self.main_window.toggle_content()

    def new_note_request(self):
        treeiter = self.model.new_note_request()
        self.selection.select_iter(treeiter)
