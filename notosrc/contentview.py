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

from gi.repository import Gtk, GLib

from notosrc.editor import NotoEditor
from notosrc.webview import WebView
from notosrc.markdown import render_markdown


# TODO: Make this a horizontal box to support side-by-side editing
class ContentView(Gtk.Bin):
    def __repr__(self):
        return '<ContentView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/contentview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.content_stack = self.builder.get_object('content_stack')
        self.content_stack.set_hexpand(True)
        self.add(self.content_stack)

        self.content_editor = NotoEditor(self.parent_window, self)
        self.content_stack.add_titled(self.content_editor, 'editor', 'Editor')

        self.content_preview = WebView(self.parent_window)
        self.content_stack.add_titled(self.content_preview, 'preview', 'Preview')

        self.content_stack.set_visible_child_name('editor')

    def preview_content(self):
        render_markdown(self.content_editor.view, self.content_preview.view)

    def in_preview_mode(self):
        return self.content_stack.get_visible_child_name() == 'preview'

    def preview_toggled(self):
        if self.content_stack.get_visible_child_name() == 'editor':
            self.content_stack.set_visible_child_name('preview')
            self.preview_content()
        else:
            self.content_stack.set_visible_child_name('editor')
