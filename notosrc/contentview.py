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

from copy import deepcopy
from gi.repository import Gtk, GLib

from notosrc.textview import TextView
from notosrc.webview import WebView
from notosrc.markdown import render_markdown


class ContentView(Gtk.Bin):
    def __repr__(self):
        return '<ContentView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/contentview.ui')
        self.slider = self.builder.get_object('slider')
        self.content = self.builder.get_object('content')
        self.content_stack = self.builder.get_object('content_stack')
        self.add(self.slider)
        self._set_up_widgets()

    def _set_up_widgets(self):
        content_editor = TextView()
        self.editor = content_editor.view
        self.content_stack.add_titled(content_editor, 'editor', 'Editor')

        content_preview = WebView()
        self.webview = content_preview.view
        self.content_stack.add_titled(content_preview, 'preview', 'Preview')

        self.content_stack.set_visible_child_name('editor')

    def preview_content(self):
        render_markdown(self.editor, self.webview)

    def _show_content_stack(self):
        duration = self.content.get_transition_duration()
        self.slider.set_hexpand(True)
        self.slider.set_reveal_child(True)
        GLib.timeout_add(duration, self.content.set_reveal_child, True)

    def _hide_content_stack(self):
        duration = self.content.get_transition_duration()
        self.content.set_reveal_child(False)
        GLib.timeout_add(duration, self.slider.set_reveal_child, False)
        GLib.timeout_add(duration, self.slider.set_hexpand, False)

    def do_size_allocate(self, allocation):
        parent_allocation = self.get_parent().get_allocation()
        sidebar_width = self.parent_window.notesview.sidebar_width

        if self.parent_window.is_showing_content():
            allocation.x = parent_allocation.x + sidebar_width
            allocation.width = parent_allocation.width - sidebar_width

            parent_allocation.width = parent_allocation.width - allocation.width
            self.parent_window.notesview.set_allocation(parent_allocation)

        Gtk.Bin.do_size_allocate(self, allocation)
