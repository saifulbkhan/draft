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

from notosrc.utils.gi_composites import GtkTemplate

@GtkTemplate(ui='/org/gnome/Noto/window.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'
    sidebar = GtkTemplate.Child()

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
        
    def _add_widgets(self):    
        self.hsize_group.add_widget(self.sidebar)
        
        titlebar = _HeaderBar(self.hsize_group)
        self.set_titlebar(titlebar)

    @GtkTemplate.Callback
    def _on_search(self, widget):
        pass

    @GtkTemplate.Callback
    def _on_select_row(self, widget):
        pass


@GtkTemplate(ui='/org/gnome/Noto/headerbar.ui')
class _HeaderBar(Gtk.Box):
    __gtype_name__ = 'HeaderBar'
    left_header = GtkTemplate.Child()

    def __repr__(self):
        return '<HeaderBar>'

    def __init__(self, hsize_group):
        Gtk.Box.__init__(self)
        self.init_template()
        hsize_group.add_widget(self.left_header)

    @GtkTemplate.Callback
    def _on_search_toggled(self, widget):
        pass

    @GtkTemplate.Callback
    def _on_preview_toggled(self, widget):
        pass
