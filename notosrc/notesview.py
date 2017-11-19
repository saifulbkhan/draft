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

from gi.repository import Gtk, GLib, Pango, Gdk
from notosrc.treestore import TreeStore

class NotesView(Gtk.Bin):
    sidebar_width = 250
    def __repr__(self):
        return '<NotesView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/notesview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.slider = self.builder.get_object('slider')
        noteslist = self.builder.get_object('noteslist')
        listview = self.builder.get_object('listview')

        self.add(self.slider)
        self.view = ListView(self.parent_window)
        listview.add(self.view)

        self.search_bar = self.builder.get_object('search_bar')
        self.search_entry = self.builder.get_object('search_entry')

    def toggle_panel(self):
        if self.slider.get_reveal_child():
            self.slider.set_reveal_child(False)
        else:
            self.slider.set_reveal_child(True)

    def search_toggled(self):
        if self.search_bar.get_search_mode():
            self.search_bar.set_search_mode(False)
            self.search_entry.set_text("")
        else:
            self.search_bar.set_search_mode(True)
            self.search_entry.grab_focus()

    def set_editor(self, editor):
        self.view.editor = editor

    def do_size_allocate(self, allocation):
        if self.parent_window.content_shown():
            allocation.width = self.sidebar_width

        Gtk.Bin.do_size_allocate(self, allocation)


class ListView(Gtk.TreeView):

    def __repr__(self):
        return '<ListView>'

    def __init__(self, window):
        Gtk.TreeView.__init__(self, TreeStore())
        self.model = self.get_model()
        self.main_window = window
        self.editor = None

        self.selection = self.get_selection()
        self.selection.connect('changed', self._on_selection_changed)

        self._populate()
        self.set_headers_visible(False)
        self.connect('key-press-event', self._on_key_press)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            # Delete row and file with (Del)
            if event.keyval == Gdk.KEY_Delete:
                self.delete_selected_row()

    def _populate(self):
        for i, title in enumerate(["title", "details", "last_edited"]):
            renderer = Gtk.CellRendererText(size_points=12,
                                            ellipsize=Pango.EllipsizeMode.END)
            renderer.set_fixed_size(-1, 36)
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_min_width(250)
            setattr(self, title, column)
            self.append_column(column)
        self.title.set_expand(True)

    def _on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if not self.main_window.is_showing_content():
            self.main_window.toggle_content()
            self.details.set_visible(False)
            self.last_edited.set_visible(False)

        self.model.prepare_for_edit(treeiter, self.editor.load_file)

    def new_note_request(self):
        treeiter = self.model.new_note_request()
        self.selection.select_iter(treeiter)

    def set_title_for_current_selection(self, title):
        model, treeiter = self.selection.get_selected()
        self.model.set_title_for_iter(treeiter, title)

    def delete_selected_row(self):
        model, treeiter = self.selection.get_selected()
        self.model.delete_row_for_iter(treeiter)
