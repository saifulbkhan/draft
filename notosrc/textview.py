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

from collections import OrderedDict
from warnings import warn

import gi
gi.require_version('WebKit', '3.0')
gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GObject, Gio, GLib, WebKit, GtkSource
from gettext import gettext as _

# Ensure that GtkBuilder actually recognises WebView and SourceView in UI file
GObject.type_ensure(GObject.GType(WebKit.WebView))
GObject.type_ensure(GObject.GType(GtkSource.View))

class TextView(Gtk.Box):
    def __repr__(self):
        return '<TextView>'

    def __init__(self, view_type='webview'):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        try:
            assert view_type in ('editor', 'webview')
        except AssertionError:
            warn("TextView can only be of 'webview' or 'editor' type")

        self.view_type = view_type
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/textview.ui')
        self._set_up_widgets()
        self.view = self.builder.get_object(self.view_type)

    def _set_up_widgets(self):
        widgets = {}

        # Use OrderedDict so that packing occurs in order of declaration
        if self.view_type == 'editor':
            widgets = OrderedDict({
                'scrollable_editor': (True, True, 0),
                'status_bar': (False, False, 0)
            })
            handler_class = EditorHandlers
        else:
            widgets = OrderedDict({
                'scrollable_webview': (True, True, 0)
            })
            handler_class = WebviewHandlers

        self.builder.connect_signals(WebviewHandlers())
        self._generate_text_view(widgets)

    def _generate_text_view(self, widgets):
        for widget_name, pack_info in widgets.items():
            widget = self.builder.get_object(widget_name)
            expand, fill, padding = pack_info
            self.pack_start(widget, expand, fill, padding)

class EditorHandlers():
    # TODO: Define signal handlers for the editor textview
    pass

class WebviewHandlers():
    def on_navigation_request(self, *args):
        webview, frame, request, navigation_action, policy_decision = args
        policy_decision.ignore()
        return True
