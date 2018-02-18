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
from notosrc.views.store import NotoListStore, TreeStore


# TODO: Another class for note groups with TreeView as view

# TODO: Make this a stack for storing multiple NotoNotesList
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
        self.slider.set_hexpand(False)
        noteslist = self.builder.get_object('noteslist')
        listview = self.builder.get_object('listview')

        self.add(self.slider)
        self.view = NotoNotesList(None)
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
        self.view.set_editor(editor)

    def new_note_request(self):
        self.view.new_note_request()


class NotoNotesList(Gtk.ListBox):
    """The listbox containing all the notes in a note group"""
    __gtype__name__ = 'NotoNotesList'

    def __repr__(self):
        return '<NotoNotesList>'

    def __init__(self, parent_group):
        """Initialize a new NotoNotesList for given @parent_group

        @parent_group: string, unique hash string for @parent_group
        """
        Gtk.ListBox.__init__(self)
        self._model = NotoListStore(parent_group)

        self.bind_model(self._model, self._create_row_widget, None)
        self.connect('key-press-event', self._on_key_press)
        self.connect('row-selected', self._on_row_selected)
        self._model.connect('items-changed', self._on_items_changed)

    def _create_row_widget(self, note_data, user_data):
        """Create a row widget for @note_data"""
        data_dict = note_data.to_dict()
        title = data_dict['title']

        label = Gtk.Label()
        self._make_title_label(label, title)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title_box.pack_start(label, True, False, 0)

        return title_box

    def _make_title_label(self, label, title):
        """Set label for @label to @title, set ellipsize, justification and
        visibility.
        """
        label.set_markup('<b>%s</b>' % title)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_halign(Gtk.Align.START)
        label.set_visible(True)
        for direction in ['left', 'right', 'top', 'bottom']:
            method = 'set_margin_%s' % direction
            getattr(label, method)(6)

    def _on_key_press(self, widget, event):
        """Handler for signal `key-press-event`"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            # Delete row and file with (Del)
            if event.keyval == Gdk.KEY_Delete:
                self.delete_selected_row()

    def _on_row_selected(self, widget, row):
        """Handler for signal `row-selected`"""
        if not row:
            return

        position = row.get_index()
        self._model.prepare_for_edit(position,
                                    self.editor.switch_view,
                                    self.editor.load_file)

    def _on_items_changed(self, model, position, removed, added):
        """Handler for model's `items-changed` signal"""
        row = self.get_row_at_index(position)
        self.select_row(row)

    def set_editor(self, editor):
        """Set editor for @self

        @self: NotoNotesList
        @editor: NotoEditor, the editor to display selected notes and listen
                 for changes that need to be conveyed to the backend
        """
        self.editor = editor
        editor.connect('title-changed', self.set_title_for_current_selection)
        editor.connect('subtitle-changed', self.set_subtitle_for_current_selection)
        editor.connect('keywords-changed', self.set_keywords_for_current_selection)

    def new_note_request(self):
        """Request for creation of a new note and append it to the list"""
        self._model.new_text_request()

    def set_title_for_current_selection(self, widget, title):
        """Set the title for currently selected note, as well as write this to
        the db.

        @self: NotoNotesList
        @title: string, the title to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'title', title)

        box = row.get_child()
        labels = box.get_children()
        label = labels[0]
        self._make_title_label(label, title)

    def set_subtitle_for_current_selection(self, widget, subtitle):
        """Set the subtitle for currently selected text, as well as write this
        to the db.

        @self: NotoNotesList
        @subtitle: string, the subtitle to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'subtitle', subtitle)

    def set_keywords_for_current_selection(self, widget, keywords):
        """Ask store to make changes to the keywords of the currently selected note
        so that it can be written to db.

        @self: NotoNotesList
        @keywords: list, the list of string keywords which the selected note will be
               tagged with.
        """
        row = self.get_selected_row()
        position = row.get_index()
        new_keywords = self._model.set_keywords_for_position(position, keywords)

        # since @new_keywords might have slightly different letter case keywords, we
        # should re-update editor keywords as well and then update statusbar, though
        # this is probably not the best place to do it.
        self.editor.current_note_data['keywords'] = new_keywords
        self.editor.statusbar.update_note_data()

    def delete_selected_row(self):
        """Delete currently selected note in the list"""
        position = self.get_selected_row().get_index()
        self._model.delete_item_at_postion(position)


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
        for i, title in enumerate(["title"]):
            renderer = Gtk.CellRendererText(size_points=12,
                                            ellipsize=Pango.EllipsizeMode.END)
            renderer.set_fixed_size(-1, 36)
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            setattr(self, title, column)
            self.append_column(column)
        self.title.set_expand(True)

    def _on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        self.model.prepare_for_edit(treeiter,
                                    self.editor.switch_view,
                                    self.editor.load_file)

    def new_note_request(self):
        treeiter = self.model.new_note_request()
        self.selection.select_iter(treeiter)

    def set_title_for_current_selection(self, title):
        model, treeiter = self.selection.get_selected()
        self.model.set_title_for_iter(treeiter, title)

    def delete_selected_row(self):
        model, treeiter = self.selection.get_selected()
        self.model.delete_row_for_iter(treeiter)
