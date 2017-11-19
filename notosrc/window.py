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

from notosrc.notesview import NotesView
from notosrc.contentview import ContentView
from notosrc.utils.gi_composites import GtkTemplate


@GtkTemplate(ui='/org/gnome/Noto/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'
    topbox = GtkTemplate.Child.widgets(1)[0]

    def __repr__(self):
        return '<ApplicationWindow>'

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Noto")
        self.init_template()

        if Gdk.Screen.get_default().get_height() < 700:
            self.maximize()
        
        self.set_icon_name("noto")
        self._set_up_actions()
        self._add_widgets()
        self.show_all()

    def _set_up_actions(self):
        action_entries = [
            ('new_note', self._new_note_request),
            ('new_notebook', self._new_notebook_request)
        ]

        for action, cb in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', cb)
            self.add_action(simple_action)

    def _add_widgets(self):
        titlebar = _HeaderBar(self)
        self.set_titlebar(titlebar)
        self._create_list_views()
        self._create_stack_views()

        self.connect('key-press-event', self._on_key_press)

    def _create_list_views(self):
        self.notesview = NotesView(self)
        self.topbox.pack_start(self.notesview, False, True, 0)

    def _create_stack_views(self):
        self.contentview = ContentView(self)
        self.topbox.pack_start(self.contentview, False, True, 0)
        self.notesview.set_editor(self.contentview.content_editor)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_F9:
                self.toggle_panel()

    def toggle_panel(self):
        self.notesview.toggle_panel()

    def toggle_content(self):
        if self.is_showing_content():
            self.contentview.hide_content_stack()
        else:
            self.contentview.show_content_stack()

    def is_showing_content(self):
        return self.contentview.slider.get_child_revealed()

    def content_shown(self):
        cond1 = self.contentview.slider.get_reveal_child()
        cond2 = self.contentview.slider.get_child_revealed()
        return cond1 and cond2

    def _new_note_request(self, action, param):
        self.notesview.view.new_note_request()

    def _new_notebook_request(self, action, param):
        pass


@GtkTemplate(ui='/org/gnome/Noto/headerbar.ui')
class _HeaderBar(Gtk.HeaderBar):
    __gtype_name__ = 'HeaderBar'
    search_button, preview_button = GtkTemplate.Child.widgets(2)

    def __repr__(self):
        return '<HeaderBar>'

    def __init__(self, parent):
        Gtk.HeaderBar.__init__(self)
        self.init_template()
        self.parent = parent

    @GtkTemplate.Callback
    def _on_search_toggled(self, widget):
        self.parent.notesview.search_toggled()

    @GtkTemplate.Callback
    def _on_preview_toggled(self, widget):
        self.parent.contentview.preview_toggled()
