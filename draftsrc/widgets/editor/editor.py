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
from string import whitespace

import gi
gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GObject, GtkSource, Gdk, GLib, Gio

from draftsrc import file
from draftsrc import db
from draftsrc.markup import MarkdownSymbols
from draftsrc.widgets.editor.statusbar import DraftStatusbar
from draftsrc.widgets.editor.thesaurusbox import DraftThesaurusBox
from draftsrc.widgets.editor.searchbox import DraftSearchBox
from draftsrc.widgets.editor.sourceview import DraftSourceView

# Ensure that GtkBuilder actually recognises SourceView in UI file
GObject.type_ensure(GObject.GType(GtkSource.View))


class DraftEditor(Gtk.Overlay):
    __gtype_name__ = 'DraftEditor'

    __gsignals__ = {
        'text-viewed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'view-transposed': (GObject.SignalFlags.RUN_FIRST,
                            None,
                            (GObject.TYPE_STRING,
                             GObject.TYPE_INT,
                             GObject.TYPE_INT)),
        'escape-edit': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    class _ViewData(object):
        markup_type = ''
        text_data = None
        source_file = None
        markup_symbols = None
        synonym_word_bounds = ()

    open_views = {}
    _current_sourceview = None
    _single_mode_name = 'single'
    _multi_mode_name = 'multi'
    _loads_in_progress = 0
    _multi_mode_order = []
    _in_fullscreen_mode = False
    _style_manager = None

    def __repr__(self):
        return '<DraftEditor>'

    def __init__(self, main_window, parent):
        Gtk.Overlay.__init__(self)
        self.main_window = main_window
        self.parent_container = parent
        self._set_up_widgets()
        self._style_manager = GtkSource.StyleSchemeManager.get_default()
        self.single_mode = True

    def _set_up_widgets(self):
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._main_box)

        self.util_revealer = Gtk.Revealer()
        self._main_box.pack_start(self.util_revealer, False, False, 0)

        self.thesaurus_box = DraftThesaurusBox()
        self.search_box = DraftSearchBox()

        self.editor_stack = Gtk.Stack()
        self._main_box.pack_start(self.editor_stack, True, True, 0)

        self.view_store = Gtk.Stack()
        self.editor_stack.add_named(self.view_store,
                                    self._single_mode_name)

        self._multi_view_stack = Gtk.Stack()
        self._multi_view_stack.set_transition_duration(500)
        self.editor_stack.add_named(self._multi_view_stack,
                                    self._multi_mode_name)

        self.statusbar = DraftStatusbar(self)
        self._main_box.pack_start(self.statusbar, False, False, 0)

        self._status_revealer = Gtk.Revealer()
        self._status_revealer.set_valign(Gtk.Align.END)
        self._status_revealer.set_vexpand(False)
        self._status_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.add_overlay(self._status_revealer)

        self.statusbar.connect('word-goal-set', self._on_word_goal_set)
        self.thesaurus_box.connect('cancel-synonym', self._on_cancel_synonym)
        self.thesaurus_box.connect('apply-synonym', self._on_apply_synonym)
        self.search_box.connect('close-search', self._on_close_search)
        self.connect('key-press-event', self._on_key_press)
        self.connect('motion-notify-event', self._on_motion_notify)

    @property
    def view(self):
        return self._current_sourceview

    @view.setter
    def view(self, sourceview):
        self._current_sourceview = sourceview
        if self.open_views[sourceview].text_data.in_trash:
            self.statusbar.set_sensitive(False)
        else:
            self.statusbar.set_sensitive(True)
        self._update_content_header_title()

    @property
    def single_mode(self):
        return self.editor_stack.get_visible_child_name() == self._single_mode_name

    @single_mode.setter
    def single_mode(self, single_mode):
        mode_name = self._single_mode_name
        if not single_mode:
            mode_name = self._multi_mode_name
        self.editor_stack.set_visible_child_name(mode_name)
        self.editor_stack.get_child_by_name(mode_name).set_visible(True)

    @property
    def current_text_data(self):
        view_data = self.open_views.get(self.view)
        return view_data.text_data

    @current_text_data.setter
    def current_text_data(self, text_data):
        view_data = self.open_views.get(self.view)
        view_data.text_data = text_data

    @property
    def _current_file(self):
        view_data = self.open_views.get(self.view)
        return view_data.source_file

    @_current_file.setter
    def _current_file(self, source_file):
        view_data = self.open_views.get(self.view)
        view_data.source_file = source_file

    @property
    def _synonym_word_bounds(self):
        view_data = self.open_views.get(self.view)
        return view_data.synonym_word_bounds

    @_synonym_word_bounds.setter
    def _synonym_word_bounds(self, bounds):
        view_data = self.open_views.get(self.view)
        view_data.synonym_word_bounds = bounds

    @property
    def _markup_symbols(self):
        view_data = self.open_views.get(self.view)
        return view_data.markup_symbols

    @property
    def markup_type(self):
        view_data = self.open_views.get(self.view)
        return view_data.markup_type

    def _prep_view(self, view):
        self.set_view_font_from_app_settings(view)
        self.set_view_typewriter_mode_from_app_settings(view)

        def on_grab_focus(widget):
            self.util_revealer.set_reveal_child(False)

        def on_key_press(widget, event):
            if event.keyval == Gdk.KEY_Escape:
                self.emit('escape-edit')

        view.connect('grab-focus', on_grab_focus)
        view.connect('key-press-event', on_key_press)
        view.connect('thesaurus-requested', self._on_thesaurus_requested)
        view.connect('insert-changed', self._on_insert_changed)

    def _prep_buffer(self, buffer, markup_type='markdown'):
        buffer.connect('modified-changed', self._on_modified_changed)
        self._place_insert_for_buffer(buffer)
        self._on_buffer_changed_id = buffer.connect('changed',
                                                    self._on_buffer_changed)
        self.set_buffer_style_scheme_from_settings(buffer)
        self.init_markup(buffer, markup_type)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if (event_and_modifiers and
                event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
            if event.keyval == Gdk.KEY_b:
                self.insert_strong()
            elif event.keyval == Gdk.KEY_i:
                self.insert_emphasis()
            elif event.keyval ==Gdk.KEY_k:
                self.insert_link()
            elif event.keyval == Gdk.KEY_f:
                self.set_utility_child(self.search_box)
                self.util_revealer.set_reveal_child(True)
                self.search_box.set_active_view(self.view)
            elif event.keyval == Gdk.KEY_t:
                self.fullscreen_statusbar_reveal(True)
                self.statusbar.show_tag_editor()
            elif event.keyval == Gdk.KEY_g:
                self.fullscreen_statusbar_reveal(True)
                self.statusbar.show_goal_editor()

    def _on_motion_notify(self, widget, event):
        if self._in_fullscreen_mode:
            x, y, width, height = event.window.get_geometry()
            if event.y_root >= height - 1:
                self._status_revealer.set_reveal_child(True)
            elif height - event.y_root > self.statusbar.get_allocated_height():
                self._status_revealer.set_reveal_child(False)

    def _on_word_goal_set(self, widget, goal):
        if self.current_text_data.word_goal != goal:
            self.current_text_data.word_goal = goal

    def _on_modified_changed(self, buffer):
        assert buffer is self.view.get_buffer()
        insert = buffer.get_insert()
        self.view.scroll_mark_onscreen(insert)

    def _on_buffer_changed(self, buffer):
        assert buffer is self.view.get_buffer()
        self._write_current_buffer()
        self._update_title_and_subtitle()
        self.statusbar.update_word_count()
        self._set_last_modified()
        GLib.idle_add(self.view.emit, 'insert-changed')

    def _on_thesaurus_requested(self, widget, word, word_start, word_end):
        self._synonym_word_bounds = (word_start, word_end)
        self.set_utility_child(self.thesaurus_box)
        self.util_revealer.set_reveal_child(True)
        self.thesaurus_box.update_for_word(word)

    def _on_cancel_synonym(self, widget):
        self.util_revealer.set_reveal_child(False)
        self.view.grab_focus()

    def _on_apply_synonym(self, widget, word):
        start, end = self._synonym_word_bounds
        buffer = self.view.get_buffer()
        buffer.delete(start, end)
        buffer.insert(start, word)
        self.util_revealer.set_reveal_child(False)
        self.view.grab_focus()

    def _on_close_search(self, widget):
        self.view.grab_focus()

    def _on_insert_changed(self, sourceview):
        buffer = sourceview.get_buffer()
        insert_mark = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert_mark)
        offset = insert_iter.get_offset()

        view_data = self.open_views.get(sourceview)
        view_data.text_data.last_edit_position = offset

    def fullscreen_mode(self):
        self._main_box.remove(self.statusbar)
        self._status_revealer.add(self.statusbar)
        self._in_fullscreen_mode = True

    def regular_mode(self):
        self._status_revealer.remove(self.statusbar)
        self._main_box.pack_start(self.statusbar, False, False, 0)
        self._in_fullscreen_mode = False

    def fullscreen_statusbar_reveal(self, reveal):
        if self._in_fullscreen_mode:
            self._status_revealer.set_reveal_child(reveal)

    def update_font_for_settings(self):
        for view in self.open_views:
            self.set_view_font_from_app_settings(view)

    def update_typewriter_mode_for_settings(self):
        for view in self.open_views:
            self.set_view_typewriter_mode_from_app_settings(view)

    def update_style_scheme_for_settings(self):
        for view in self.open_views:
            self.set_buffer_style_scheme_from_settings(view.get_buffer())

    def set_view_font_from_app_settings(self, view):
        font_name = self.main_window.app_settings.get_string('editor-font')
        view.set_font(font_name)

    def set_view_typewriter_mode_from_app_settings(self, view):
        typewriter_mode = self.main_window.app_settings.get_enum('typewriter-mode')
        if typewriter_mode:
            view.set_typewriter_mode(True, typewriter_mode)
        else:
            view.set_typewriter_mode(False)

    def set_buffer_style_scheme_from_settings(self, buffer):
        scheme_id = self.main_window.app_settings.get_string('color-scheme')
        if scheme_id:
            color_scheme = self._style_manager.get_scheme(scheme_id)
            buffer.set_style_scheme(color_scheme)

    def get_preview_data(self):
        data = []
        if len(self._multi_mode_order) <= 1:
            row = (str(self.current_text_data.id),
                   self.markup_type,
                   self.get_text())
            data.append(row)
        else:
            for id in self._multi_mode_order:
                view, view_data = self._view_for_id(id)
                markup_type = view_data.markup_type
                text = self.get_text(view)
                data.append((id, markup_type, text))

        return data, str(self.current_text_data.id)

    def get_export_title(self):
        if len(self._multi_mode_order) <= 1:
            return self.current_text_data.title
        else:
            id = self._multi_mode_order[0]
            view, view_data = self._view_for_id(id)
            return view_data.text_data.title

    def get_text(self, view=None):
        if not view:
            view = self.view

        buffer = view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, True)
        return text

    def add_tag(self, tag):
        if tag in self.current_text_data.tags:
            return

        taglist = self.current_text_data.tags[:]
        taglist.append(tag)
        self.current_text_data.tags = taglist
        self.statusbar.update_text_data()

    def delete_tag(self, tag):
        if tag not in self.current_text_data.tags:
            return

        taglist = self.current_text_data.tags[:]
        index = taglist.index(tag)
        taglist.pop(index)
        self.current_text_data.tags = taglist
        self.statusbar.update_text_data()

    def init_markup(self, buffer, markup_type):
        view = self._view_for_buffer(buffer)
        view_data = self.open_views.get(view)
        view_data.markup_type = markup_type
        if markup_type == 'markdown':
            view_data.markup_symbols = MarkdownSymbols()

        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language(markup_type)
        buffer.set_language(language)

    def set_markup(self, markup_type):
        if self.current_text_data.markup != markup_type:
            self.current_text_data.markup = markup_type

    def set_utility_child(self, child):
        current_child = self.util_revealer.get_child()
        if current_child:
            self.util_revealer.remove(current_child)
        child.set_visible(True)
        self.util_revealer.add(child)

    def switch_view(self, texts_data):
        if self._loads_in_progress:
            return

        self.util_revealer.set_reveal_child(False)

        # clear multi view stack
        for scrolled in self._multi_view_stack.get_children():
            view = scrolled.get_child()
            id = self._id_for_view(view)
            self._multi_view_stack.remove(scrolled)
            self.view_store.add_named(scrolled, id)
        self._multi_mode_order.clear()

        if len(texts_data) > 1:
            self.single_mode = False
        else:
            self.single_mode = True

        buffers = {}
        for i, data in enumerate(texts_data):
            self.emit('text-viewed', data)
            id = str(data.id)

            scrolled = self.view_store.get_child_by_name(id)
            if scrolled:
                view = scrolled.get_child()
                assert view in self.open_views

                view_data = self.open_views.get(view)
                if view_data.text_data is not data:
                    view_data.text_data = data
                    self._refresh_view(view)

                self._prep_view(view)

                if self.single_mode:
                    self.view_store.set_visible_child(scrolled)
                else:
                    self.view_store.remove(scrolled)
                    self._multi_view_stack.add_named(scrolled, id)
                    self._multi_mode_order.append(id)

                if i == 0:
                    self.view = view
                    self.statusbar.update_state()
                    if not self.single_mode:
                        vadj = scrolled.get_vadjustment()
                        vadj.set_value(vadj.get_lower())
                        self._multi_view_stack.set_visible_child(scrolled)

                if i == len(texts_data) - 1:
                    self._update_content_header_title()

                if self.parent_container.in_preview_mode():
                    self.parent_container.preview_content()

                continue

            view = DraftSourceView()
            view_data = self._ViewData()
            self.open_views[view] = view_data
            view_data.text_data = data
            self._prep_view(view)

            scrolled = Gtk.ScrolledWindow(None, None)
            scrolled.add(view)
            scrolled.set_visible(True)
            scrolled.connect('edge-overshot', self._on_edge_overshot)
            scrolled.connect('scroll-event', self._on_scroll_event)

            if self.single_mode:
                child = self.view_store.get_child_by_name(id)
                if child:
                    self.view_store.remove(child)
                self.view_store.add_named(scrolled, id)
                self.view_store.set_visible_child(scrolled)
            else:
                self._multi_view_stack.add_named(scrolled, id)
                self._multi_mode_order.append(id)

            if i == 0:
                self.view = view
                if not self.single_mode:
                    self._multi_view_stack.set_visible_child(scrolled)

            self._loads_in_progress += 1
            buffers[data.id] = view.get_buffer()

        return buffers

    def load_file(self, gsf, buffer):
        if gsf:
            view = self._view_for_buffer(buffer)
            assert view is not None
            view_data = self.open_views.get(view)
            view_data.source_file = gsf
            self._prep_buffer(buffer)
            self._loads_in_progress -= 1
            if view_data.text_data.in_trash:
                view.set_editable(False)
            else:
                view.set_editable(True)

        if self.parent_container.in_preview_mode():
            self.parent_container.preview_content()

        if self._loads_in_progress == 0:
            self._update_content_header_title()

        self.statusbar.update_state()

    def focus_view(self, scroll_to_insert=False):
        self.view.grab_focus()

        if scroll_to_insert:
            insert = self.view.get_buffer().get_insert()
            GLib.idle_add(self.view.scroll_mark_onscreen, insert)

    def _view_for_buffer(self, buffer):
        for view in self.open_views:
            if view.get_buffer() is buffer:
                return view
        return None

    def _view_for_id(self, id):
        for view in self.open_views:
            view_data = self.open_views.get(view)
            if view_data.text_data.id == int(id):
                return view, view_data
        return None, None

    def _id_for_view(self, view):
        view_data = self.open_views.get(view)
        return str(view_data.text_data.id)

    def multi_mode_next(self):
        if not self.single_mode:
            current = self._multi_view_stack.get_visible_child_name()
            index = -1
            try:
                index = self._multi_mode_order.index(current)
            except ValueError as err:
                # TODO: (notify) current visible child not in order list.
                pass
            next_index = index + 1
            if next_index < len(self._multi_mode_order):
                next = self._multi_mode_order[next_index]
                next_child = self._multi_view_stack.get_child_by_name(next)
                vadj = next_child.get_vadjustment()
                vadj.set_value(vadj.get_lower())
                self._multi_view_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP)
                self._multi_view_stack.set_visible_child(next_child)
                self.view = next_child.get_child()
                self.statusbar.update_state()

    def multi_mode_prev(self):
        if not self.single_mode:
            current = self._multi_view_stack.get_visible_child_name()
            index = -1
            try:
                index = self._multi_mode_order.index(current)
            except ValueError as err:
                # TODO: (notify) current visible child not in order list.
                pass
            prev_index = index - 1
            if not prev_index < 0:
                prev = self._multi_mode_order[prev_index]
                prev_child = self._multi_view_stack.get_child_by_name(prev)
                vadj = prev_child.get_vadjustment()
                vadj.set_value(vadj.get_upper())
                self._multi_view_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_DOWN)
                self._multi_view_stack.set_visible_child(prev_child)
                self.view = prev_child.get_child()
                self.statusbar.update_state()

    def _on_edge_overshot(self, scrolled, edge):
        if edge == Gtk.PositionType.TOP:
            self.multi_mode_prev()
        elif edge == Gtk.PositionType.BOTTOM:
            self.multi_mode_next()

    def _on_scroll_event(self, scrolled, scroll_event):
        vadj = scrolled.get_vadjustment()
        cannot_scroll_child = vadj.get_upper() == vadj.get_page_size()
        if cannot_scroll_child:
            _, del_x, del_y = scroll_event.get_scroll_deltas()
            if scroll_event.direction == Gdk.ScrollDirection.UP or del_y < 0:
                self.multi_mode_prev()
            elif scroll_event.direction == Gdk.ScrollDirection.DOWN or del_y > 0:
                self.multi_mode_next()

    def _refresh_view(self, view):
        view_data = self.open_views.get(view)
        text_data = view_data.text_data

        filename = text_data.hash_id
        parent_dir = file.sep.join(text_data.parents)
        fpath = file.join(file.BASE_TEXT_DIR, parent_dir, filename)
        if text_data.in_trash:
            fpath = file.join(file.TRASH_DIR, filename)
        f = Gio.File.new_for_path(fpath)
        view_data.source_file.set_location(f)

        if text_data.in_trash:
            view.set_editable(False)
        else:
            view.set_editable(True)

    def _write_current_buffer(self):
        if not self.view or not self._current_file:
            return

        buffer = self.view.get_buffer()
        file.write_to_source_file_async(self._current_file,
                                        buffer)

    def _place_insert_for_buffer(self, buffer):
        view = self._view_for_buffer(buffer)
        view_data = self.open_views.get(view)
        last_edited_position = view_data.text_data.last_edit_position
        if last_edited_position is not None:
            insert_iter = buffer.get_iter_at_offset(last_edited_position)
            buffer.place_cursor(insert_iter)

        return buffer.get_insert()

    def _set_last_modified(self):
        datetime = db.get_datetime()
        self.current_text_data.last_modified = datetime

    def _update_title_and_subtitle(self):
        content = self.get_text()
        title, subtitle = self._get_title_and_subtitle_for_text(content)

        if title != self.current_text_data.title:
            self.current_text_data.title = title

        if subtitle != self.current_text_data.subtitle:
            self.current_text_data.subtitle = subtitle

    def _update_content_header_title(self):
        text = self.get_text()
        title, subtitle = self._get_title_and_subtitle_for_text(text)
        if not self.view.get_editable():
            title = title + " " + _("[Read-Only]")

        id = self._id_for_view(self.view)
        index = -1
        if id in self._multi_mode_order:
            index = self._multi_mode_order.index(id)
        self.emit('view-transposed', title, index+1, len(self._multi_mode_order))

    def _get_title_and_subtitle_for_text(self, text):
        # TODO: title identifier for specific markup, only markdown for now
        header_symbol = '#'

        stripped = text.strip(header_symbol + whitespace)
        split = stripped.split('\n', maxsplit=1)
        title = split[0]

        if not title:
            return _("Untitled"), None

        if len(split) > 1:
            subtitle = split[1].strip().split('\n', maxsplit=1)[0]
            return title, subtitle

        return title, None

    def _insert_markup_element(self, text_to_insert, block_level=0, is_list=False):
        buffer = self.view.get_buffer()
        insert_mark = buffer.get_insert()
        insert = buffer.get_iter_at_mark(insert_mark)

        if block_level:
            if buffer.is_on_empty_line(insert) and block_level == 2:
                buffer.insert(insert, '\n')
            else:
                buffer.insert(insert, '\n' * block_level)

        if is_list:
            # if already on a list item, create a sub-list.
            on_list_item, para_indentation = buffer.is_on_list_item(insert)
            if on_list_item:
                buffer.insert(insert, ' ' * para_indentation)

        left, right = text_to_insert.split(self._markup_symbols.cursor_string,
                                           maxsplit=1)
        chars_back = len(right)
        buffer.insert(insert, left+right)
        insert.backward_chars(chars_back)
        buffer.place_cursor(insert)

    def insert_heading(self, level=1):
        text_to_insert = getattr(self._markup_symbols, 'h' + str(level))
        self._insert_markup_element(text_to_insert, block_level=2)

    def insert_divider(self):
        text_to_insert = self._markup_symbols.divider
        self._insert_markup_element(text_to_insert, block_level=2)

    def insert_strong(self):
        text_to_insert = self._markup_symbols.bold
        buffer = self.view.get_buffer()
        selected = buffer.get_selection_bounds()
        if selected:
            start, end = selected
            self.strong_wrap_selected(buffer, start, end)
        else:
            self._insert_markup_element(text_to_insert)

    def insert_emphasis(self):
        text_to_insert = self._markup_symbols.italics
        buffer = self.view.get_buffer()
        selected = buffer.get_selection_bounds()
        if selected:
            start, end = selected
            self.emphasis_wrap_selected(buffer, start, end)
        else:
            self._insert_markup_element(text_to_insert)

    def insert_ordered_list(self):
        text_to_insert = self._markup_symbols.ordered_list
        self._insert_markup_element(text_to_insert, block_level=1, is_list=True)

    def insert_unordered_list(self):
        text_to_insert = self._markup_symbols.unordered_list
        self._insert_markup_element(text_to_insert, block_level=1, is_list=True)

    def insert_block_quote(self):
        text_to_insert = self._markup_symbols.block_quote
        self._insert_markup_element(text_to_insert, block_level=1)

    def insert_link(self):
        text_to_insert = self._markup_symbols.link
        buffer = self.view.get_buffer()
        selected = buffer.get_selection_bounds()
        if selected:
            start, end = selected
            self.link_wrap_selected(buffer, start, end)
        else:
            self._insert_markup_element(text_to_insert)

    def insert_image(self):
        text_to_insert = self._markup_symbols.image
        self._insert_markup_element(text_to_insert, block_level=2)

    def insert_footnote(self):
        text_to_insert = self._markup_symbols.footnote
        self._insert_markup_element(text_to_insert)

    def insert_code(self):
        text_to_insert = self._markup_symbols.code
        self._insert_markup_element(text_to_insert)

    def insert_code_block(self):
        text_to_insert = self._markup_symbols.code_block
        self._insert_markup_element(text_to_insert, block_level=2)

    def handle_generic_insert(self, button, identifier):
        if identifier == 'h1':
            self.insert_heading(1)
        elif identifier == 'h2':
            self.insert_heading(2)
        elif identifier == 'h3':
            self.insert_heading(3)
        elif identifier == 'h4':
            self.insert_heading(4)
        elif identifier == 'h5':
            self.insert_heading(5)
        elif identifier == 'h6':
            self.insert_heading(6)
        else:
            insert_fn = getattr(self, 'insert_' + identifier)
            insert_fn()

        self.view.grab_focus()

    @staticmethod
    def _wrap_with_elements(buffer, start, end, left, right):
        # before inserting, preserve the end position
        mark = buffer.create_mark(None, end)

        buffer.begin_user_action()
        buffer.insert(start, left)
        end = buffer.get_iter_at_mark(mark)
        buffer.insert(end, right)
        buffer.end_user_action()

        buffer.select_range(end, end)

    def strong_wrap_selected(self, buffer, start, end):
        text_to_insert = self._markup_symbols.bold
        left, right = text_to_insert.split(self._markup_symbols.cursor_string)
        self._wrap_with_elements(buffer, start, end, left, right)

    def emphasis_wrap_selected(self, buffer, start, end):
        text_to_insert = self._markup_symbols.italics
        left, right = text_to_insert.split(self._markup_symbols.cursor_string)
        self._wrap_with_elements(buffer, start, end, left, right)

    def link_wrap_selected(self, buffer, start, end):
        text_to_insert = self._markup_symbols.link
        left, right = text_to_insert.split(self._markup_symbols.cursor_string)
        self._wrap_with_elements(buffer, start, end, left, right)
