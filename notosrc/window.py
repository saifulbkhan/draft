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

from notosrc.textview import TextView
from notosrc.webview import WebView
from notosrc.markdown import render_markdown
from notosrc.utils.gi_composites import GtkTemplate

@GtkTemplate(ui='/org/gnome/Noto/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'
    sidebar, search_bar, search_entry, \
    notes_list, content_stack, content, \
    slider, action = GtkTemplate.Child.widgets(8)

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
        self._add_widgets()
        self.width = 0
        self.content_width_style = 'noto-content-540'

    def _add_widgets(self):
        self.hsize_group.add_widget(self.sidebar)

        titlebar = _HeaderBar(self)
        self.set_titlebar(titlebar)
        self._create_stack_views()

    def _create_stack_views(self):
        content_editor = TextView()
        self.editor = content_editor.view
        self.content_stack.add_titled(content_editor, 'editor', 'Editor')

        content_preview = WebView()
        self.webview = content_preview.view
        self.content_stack.add_titled(content_preview, 'preview', 'Preview')

        self.content_stack.show_all()
        self.content_stack.set_visible_child_name('editor')

    def preview_content(self):
        render_markdown(self.editor, self.webview)

    def _set_desired_width_style(self):
        context = self.content_stack.get_style_context()
        context.remove_class(self.content_width_style)
        if self.width <= 1050:
            self.content_width_style = 'noto-content-540'
        elif self.width > 1050 and self.width <= 1250:
            self.content_width_style = 'noto-content-740'
        elif self.width > 1250 and self.width <= 1450:
            self.content_width_style = 'noto-content-940'
        elif self.width > 1450 and self.width <= 1650:
            self.content_width_style = 'noto-content-1140'
        elif self.width > 1650 and self.width <= 1850:
            self.content_width_style = 'noto-content-1340'
        elif self.width > 1850:
            self.content_width_style = 'noto-content-1540'
        context.add_class(self.content_width_style)

    @GtkTemplate.Callback
    def _on_search(self, widget):
        pass

    @GtkTemplate.Callback
    def _on_select_row(self, widget):
        pass

    @GtkTemplate.Callback
    def _on_top_resized(self, widget, allocation):
        self.width = self.get_allocation().width
        self._set_desired_width_style()

    @GtkTemplate.Callback
    def _on_action(self, widget):
        duration = self.content.get_transition_duration()
        if self.slider.get_reveal_child():
            self.content.set_reveal_child(False)
            GLib.timeout_add(duration, self.slider.set_reveal_child, False)
            GLib.timeout_add(duration, self.slider.set_hexpand, False)
        else:
            self.slider.set_hexpand(True)
            self.slider.set_reveal_child(True)
            GLib.timeout_add(duration, self.content.set_reveal_child, True)


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
        if self.parent.search_bar.get_search_mode():
            self.parent.search_bar.set_search_mode(False)
            self.parent.search_entry.set_text("")
        else:
            self.parent.search_bar.set_search_mode(True)
            self.parent.search_entry.grab_focus()

    @GtkTemplate.Callback
    def _on_preview_toggled(self, widget):
        if self.parent.content_stack.get_visible_child_name() == 'editor':
            self.parent.content_stack.set_visible_child_name('preview')
            self.parent.preview_content()
        else:
            self.parent.content_stack.set_visible_child_name('editor')
