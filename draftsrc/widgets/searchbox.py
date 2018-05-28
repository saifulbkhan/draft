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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from gi.repository import Gtk, GObject, Gdk


class DraftSearchBox(Gtk.Bin):
    __gtype_name__ = 'DraftSearchBox'

    __gsignals__ = {
        'close-search': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _active_buffer = None
    _active_view = None

    def __repr__(self):
        return '<DraftSearchBox>'

    def __init__(self):
        Gtk.Bin.__init__(self)
        self._set_up_widgets()
        self.connect('key-press-event', self._on_key_press)
        self.connect('close-search', self._on_close_search)

    def _set_up_widgets(self):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Draft/searchbox.ui')

        search_box = builder.get_object('search_box')
        self.add(search_box)

        self._search_entry = builder.get_object('search_entry')
        self._replace_entry = builder.get_object('replace_entry')
        self._next_button = builder.get_object('next_button')
        self._prev_button = builder.get_object('prev_button')
        self._replace_mode_button = builder.get_object('replace_mode_button')
        self._search_settings_button = builder.get_object('search_settings_button')
        self._replace_button = builder.get_object('replace_button')
        self._replace_all_button = builder.get_object('replace_all_button')
        self._case_sensitive_check = builder.get_object('case_sensitive_check')
        self._whole_words_check = builder.get_object('whole_words_check')
        self._replace_revealer = builder.get_object('replace_revealer')
        self._occurrence_revealer = builder.get_object('occurrence_revealer')
        self._search_settings_popover = builder.get_object('search_settings_popover')
        self._search_occurrence_label = builder.get_object('search_occurrence_label')

        self._search_entry.connect('changed', self._on_search_changed)
        self._search_entry.connect('activate', self._on_search_activated)
        self._search_entry.connect('key-press-event', self._on_key_press)
        self._replace_entry.connect('activate', self._on_replace_activated)
        self._replace_entry.connect('key-press-event', self._on_key_press)
        self._next_button.connect('clicked', self._on_next_clicked)
        self._prev_button.connect('clicked', self._on_prev_clicked)
        self._replace_mode_button.connect('toggled',
                                          self._on_replace_mode_toggled)
        self._search_settings_button.connect('toggled',
                                             self._on_search_settings_toggled)
        self._replace_button.connect('clicked', self._on_replace_activated)
        self._replace_all_button.connect('clicked',
                                         self._on_replace_all_clicked)
        self._case_sensitive_check.connect('toggled',
                                           self._on_case_sensitive_toggled)
        self._whole_words_check.connect('toggled',
                                        self._on_whole_words_toggled)
        self._search_settings_popover.connect('closed',
                                              self._on_search_popover_closed)

    def set_active_view(self, sourceview):
        self._active_view = sourceview
        self._active_buffer = sourceview.get_buffer()
        self._replace_button.set_sensitive(False)
        self._search_entry.grab_focus()
        selected_text = self._active_buffer.get_selected_text()
        if selected_text:
            self._search_entry.set_text(selected_text)
            self._update_occurrences_count()
        else:
            self._update_occurrences_count()

    def _scroll_to_selection(self):
        start, end = self._active_buffer.get_selection_bounds()
        if start and end:
            mark = self._active_buffer.create_mark(None, end, True)
            self._active_view.scroll_mark_onscreen(mark)
            self._active_buffer.delete_mark(mark)

    def _update_occurrences_count(self):
        self._active_buffer.find_matches(self._search_entry.get_text())
        num_occurrences = self._active_buffer.get_occurrences_count()
        if num_occurrences < 1:
            self._occurrence_revealer.set_reveal_child(False)
            self._replace_all_button.set_sensitive(False)
            if self._search_entry.get_text():
                self._search_entry.get_style_context().add_class('error')
            else:
                self._search_entry.get_style_context().remove_class('error')
        else:
            self._search_occurrence_label.set_label("%s matches found" % num_occurrences)
            self._occurrence_revealer.set_reveal_child(True)
            self._search_entry.get_style_context().remove_class('error')
            self._replace_all_button.set_sensitive(True)

        self._replace_button.set_sensitive(False)
        self._active_buffer.unselect_any()

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_Escape:
                self.emit('close-search')
                self._active_buffer.unselect_any()

    def _on_close_search(self, widget):
        self._active_buffer.finish_current_search()

    def _on_search_changed(self, widget):
        self._update_occurrences_count()

    def _on_search_activated(self, widget):
        self._active_buffer.select_next_match()
        self._replace_button.set_sensitive(True)
        self._scroll_to_selection()

    def _on_replace_activated(self, widget):
        self._active_buffer.replace_current_match(self._replace_entry.get_text())
        self._update_occurrences_count()
        self._active_buffer.select_next_match()
        self._replace_button.set_sensitive(True)

    def _on_next_clicked(self, widget):
        self._active_buffer.select_next_match()
        self._replace_button.set_sensitive(True)
        self._scroll_to_selection()

    def _on_prev_clicked(self, widget):
        self._active_buffer.select_prev_match()
        self._replace_button.set_sensitive(True)
        self._scroll_to_selection()

    def _on_replace_mode_toggled(self, widget):
        if self._replace_mode_button.get_active():
            self._replace_revealer.set_reveal_child(True)
        else:
            self._replace_revealer.set_reveal_child(False)

    def _on_search_settings_toggled(self, widget):
        self._search_settings_popover.popup()

    def _on_replace_all_clicked(self, widget):
        self._active_buffer.replace_all_matches(self._replace_entry.get_text())
        self._update_occurrences_count()

    def _on_case_sensitive_toggled(self, widget):
        self._active_buffer.set_search_case_sensitivity(widget.get_active())
        self._update_occurrences_count()

    def _on_whole_words_toggled(self, widget):
        self._active_buffer.set_search_whole_words_only(widget.get_active())
        self._update_occurrences_count()

    def _on_search_popover_closed(self, widget):
        self._search_settings_button.set_active(False)
