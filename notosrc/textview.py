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
from warnings import warn, UserWarning

from gi.repository import Gtk, Gio, GLib
from gettext import gettext as _

class TextView(Gtk.Box):
    def __repr__(self):
        return '<TextView>'

    def __init__(self, view_type='webview'):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        try:
            assert view_type in ('editor', 'webview')
        except AssertionError:
            warn("TextView can only be of 'webview' or 'editor' type",
                 UserWarning)

        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/textview.ui')
        widgets = {}

        if view_type == 'editor':
            widgets = OrderedDict({
                'scrollable_editor': (True, True, 0),
                'status_bar': (False, False, 0)
            })
            self.builder.connect_signals(EditorHandlers())
        else:
            # TODO: Generate the other type of TextView and connect handlers
            pass

        self._generate_text_view(widgets)

    def _generate_text_view(self, widgets):
        for widget_name, pack_info in widgets.items():
            widget = self.builder.get_object(widget_name)
            expand, fill, padding = pack_info
            self.pack_start(widget, expand, fill, padding)

class EditorHandlers():
    # TODO: Define signal handlers for the editor textview
    pass
