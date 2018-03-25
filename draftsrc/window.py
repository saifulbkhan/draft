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

from gi.repository import Gtk, Gdk, Gio, GLib
from gettext import gettext as _

from draftsrc.views.panelview import DraftTextListView, DraftLibraryView
from draftsrc.views.contentview import ContentView


class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    group_panel_hidden = False
    text_panel_hidden = False
    lock_group_panel = False
    lock_text_panel = False

    def __repr__(self):
        return '<ApplicationWindow>'

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Draft")

        self.set_default_size(800, 600)

        if Gdk.Screen.get_default().get_height() < 700:
            self.maximize()

        self.set_icon_name("draft")
        self._set_up_actions()
        self._set_up_widgets()
        self.show_all()

    def _set_up_actions(self):
        action_entries = [
            ('new_text', self._new_text_request),
            ('new_group', self._new_group_request)
        ]

        for action, cb in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', cb)
            self.add_action(simple_action)

    def _set_up_widgets(self):
        titlebar = _DraftHeaderBar(self)
        self.set_titlebar(titlebar)

        self._topbox = Gtk.Box()
        self.add(self._topbox)

        self._set_up_panel_views()
        self._set_up_content_view()
        GLib.idle_add(self.libraryview.select_appropriate_row)
        self.connect('key-press-event', self._on_key_press)

    def _set_up_panel_views(self):
        self.libraryview = DraftLibraryView(self)
        self._topbox.pack_start(self.libraryview, False, True, 0)
        self.textlistview = DraftTextListView(self)
        self._topbox.pack_start(self.textlistview, False, True, 0)

    def _set_up_content_view(self):
        self.contentview = ContentView(self)
        self._topbox.pack_start(self.contentview, False, True, 0)
        # TODO: make this switchable, when supporting side-by-side editing
        self.textlistview.set_editor(self.contentview.content_editor)

    def _new_text_request(self, action, param):
        self.textlistview.new_text_request()

    def _new_group_request(self, action, param):
        self.libraryview.new_group_request()

    def _escape_selection_modes(self):
        self.textlistview.escape_selection_mode()
        self.libraryview.escape_selection_mode()

    def _on_key_press(self, widget, event):
        modifier = Gtk.accelerator_get_default_mod_mask()
        modifier = (event.state & modifier)

        if modifier:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK

            if (event.keyval == Gdk.KEY_F9
                    and modifier == control_mask
                    and not self.lock_group_panel):
                if self.group_panel_hidden:
                    self.reveal_group_panel()
                    if not self.lock_text_panel:
                        self.reveal_text_panel()
                else:
                    self.hide_group_panel()
        else:
            if (event.keyval == Gdk.KEY_F9
                    and not self.lock_text_panel
                    and not self.lock_group_panel):
                if self.text_panel_hidden:
                    self.reveal_text_panel()
                else:
                    self.hide_text_panel()
                    self.hide_group_panel()
            elif event.keyval == Gdk.KEY_Escape:
                self._escape_selection_modes()

    def hide_group_panel(self):
        self.libraryview.hide_panel()
        self.group_panel_hidden = True

    def reveal_group_panel(self):
        self.libraryview.reveal_panel()
        self.group_panel_hidden = False

    def hide_text_panel(self):
        self.textlistview.hide_panel()
        self.text_panel_hidden = True

    def reveal_text_panel(self):
        self.textlistview.reveal_panel()
        self.text_panel_hidden = False

    def update_content_view_and_headerbar(self):
        if self.libraryview.collection_is_empty():
            self.contentview.set_empty_collection_state()
            self.hide_headerbar_elements()
            self.hide_group_panel()
            self.hide_text_panel()
            self.lock_group_panel = True
            self.lock_text_panel = True
        elif self.libraryview.selected_group_has_no_texts():
            self.contentview.set_empty_group_state()
            self.show_headerbar_elements()
            self.partial_headerbar_interaction()
            self.hide_text_panel()
            self.lock_group_panel = False
            self.lock_text_panel = True
        else:
            self.contentview.set_last_content_state()
            self.show_headerbar_elements()
            self.complete_headerbar_interaction()
            self.reveal_text_panel()
            self.lock_group_panel = False
            self.lock_text_panel = False

    def hide_headerbar_elements(self):
        headerbar = self.get_titlebar()
        headerbar.set_elements_visible(False)

    def show_headerbar_elements(self):
        headerbar = self.get_titlebar()
        headerbar.set_elements_visible(True)

    def partial_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_sensitive(False)

    def complete_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_sensitive(True)


class _DraftHeaderBar(Gtk.Box):
    __gtype_name__ = 'DraftHeaderBar'

    def __repr__(self):
        return '<DraftHeaderBar>'

    def __init__(self, parent):
        Gtk.Box.__init__(self)
        self.parent = parent
        self._set_up_widgets()

    def _set_up_widgets(self):
        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/org/gnome/Draft/headerbar.ui')

        self._headerbar = self._builder.get_object('HeaderBar')
        self.pack_start(self._headerbar, True, True, 0)

        self._search_button = self._builder.get_object('search_button')
        self._search_button.connect('toggled', self._on_search_toggled)
        self._preview_button = self._builder.get_object('preview_button')
        self._preview_button.connect('toggled', self._on_preview_toggled)
        self._new_button = self._builder.get_object('new_button')

    def _on_search_toggled(self, widget):
        self.parent.textlistview.search_toggled()

    def _on_preview_toggled(self, widget):
        self.parent.contentview.preview_toggled()

    def set_elements_visible(self, visible):
        self._new_button.set_visible(visible)
        self._search_button.set_visible(visible)
        self._preview_button.set_visible(visible)

    def set_preview_button_sensitive(self, sensitive):
        self._preview_button.set_sensitive(sensitive)
