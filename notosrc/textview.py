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
from gettext import gettext as _

import gi
gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GObject, GtkSource, Gdk

from notosrc import file

# Ensure that GtkBuilder actually recognises SourceView in UI file
GObject.type_ensure(GObject.GType(GtkSource.View))

class TextView(Gtk.Box):
    def __repr__(self):
        return '<TextView>'

    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/textview.ui')
        self.main_window = parent
        self.view = self.builder.get_object('editor')
        self._set_up_widgets()
        self.current_file = None
        self.current_file_etag = None

    def _set_up_widgets(self):
        # Use OrderedDict so that packing occurs in order of declaration
        widgets = OrderedDict({
            'scrollable_editor': (True, True, 0),
            'status_bar': (False, False, 0)
        })
        self.connect('key-press-event', self._on_key_press)

        buffer = self.view.get_buffer()
        self._on_buffer_changed_id = buffer.connect('changed',
                                                    self._on_buffer_changed)
        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language('markdown')
        buffer.set_language(language)

        self._generate_text_view(widgets)

    def _generate_text_view(self, widgets):
        for widget_name, pack_info in widgets.items():
            widget = self.builder.get_object(widget_name)
            expand, fill, padding = pack_info
            self.pack_start(widget, expand, fill, padding)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if event_and_modifiers:
            # Save file with (Ctrl + S)
            if (event.keyval == Gdk.KEY_s
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                if self.main_window.content_shown():
                    self.write_current_buffer()

    def _on_buffer_changed(self, buffer):
        count = buffer.get_char_count()
        self.write_current_buffer()

    def load_file(self, res):
        self.current_file_etag = None
        if res:
            self.current_file, contents, self.current_file_etag = res
            self.render_content(contents)

    def render_content(self, contents):
        buffer = self.view.get_buffer()
        with buffer.handler_block((self._on_buffer_changed_id)):
            buffer.set_text(contents)

    def write_current_buffer(self):
        buffer = self.view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()

        def on_file_write(f, etag):
            self.current_file_etag = etag

        text_content = buffer.get_text(start, end, False)
        if not text_content:
            self.current_file_etag = file.write_to_file(self.current_file,
                                                        text_content,
                                                        self.current_file_etag)
        else:
            file.write_to_file_async(self.current_file,
                                     text_content,
                                     on_file_write)

        title = self._get_title_for_text(text_content)
        self.main_window.notesview.view.set_title_for_current_selection(title)

    def _get_title_for_text(self, text):
        stripped = text.lstrip()
        split = stripped.split('\n', maxsplit=1)
        title = split[0]

        if not title:
            return _("Untitled")
        # Strip any leading '#'s from the title
        elif title[0] == '#':
            title = title[1:]
            return self._get_title_for_text(title)

        return title
