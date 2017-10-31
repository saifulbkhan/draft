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
        self.hsize_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
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

    def _create_list_views(self):
        self.notesview = NotesView(self)
        self.topbox.pack_start(self.notesview, False, True, 0)

    def _create_stack_views(self):
        self.contentview = ContentView(self)
        self.topbox.pack_start(self.contentview, False, True, 0)
        self.notesview.set_editor(self.contentview.content_editor)

    def toggle_content(self):
        if self.is_showing_content():
            self.contentview._hide_content_stack()
        else:
            self.contentview._show_content_stack()

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
class _HeaderBar(Gtk.Box):
    __gtype_name__ = 'HeaderBar'
    left_header, right_header, content_title, \
    search_button, preview_button = GtkTemplate.Child.widgets(5)

    def __repr__(self):
        return '<HeaderBar>'

    def __init__(self, parent):
        Gtk.Box.__init__(self)
        self.init_template()
        self.parent = parent
        parent.hsize_group.add_widget(self.left_header)
        self._update_decorations (Gtk.Settings.get_default(), None)

    def _update_decorations(self, settings, pspec):
        layout_desc = settings.props.gtk_decoration_layout;
        tokens = layout_desc.split(":", 1)
        if len(tokens) > 1:
            self.right_header.props.decoration_layout = ":" + tokens[1]
        else:
            self.right_header.props.decoration_layout = ""
        self.left_header.props.decoration_layout = tokens[0]

    @GtkTemplate.Callback
    def _on_search_toggled(self, widget):
        self.parent.notesview.search_toggled()

    @GtkTemplate.Callback
    def _on_preview_toggled(self, widget):
        self.parent.contentview.preview_toggled()
