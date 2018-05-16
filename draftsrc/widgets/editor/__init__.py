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

from gi.repository import Gtk, GObject, GtkSource, Gdk, GLib

from draftsrc import file
from draftsrc import db
from draftsrc.parsers.markup import MarkdownSymbols
from draftsrc.widgets.statusbar import DraftStatusbar
from draftsrc.widgets.thesaurusbox import DraftThesaurusBox
from draftsrc.widgets.editor.sourceview import DraftSourceView

# Ensure that GtkBuilder actually recognises SourceView in UI file
GObject.type_ensure(GObject.GType(GtkSource.View))


class DraftEditor(Gtk.Box):
    __gtype_name__ = 'DraftEditor'

    __gsignals__ = {
        'text-viewed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'title-changed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'subtitle-changed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'markup-changed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'word-goal-set': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_INT,)),
        'tags-changed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'view-changed': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,))
    }

    # markup type of currently selected text
    markup_type = 'markdown'
    view = None
    current_text_data = None
    _current_file = None
    _open_files = {}
    _load_in_progress = False
    _synonym_word_bounds = ()
    _markup_symbols = None

    def __repr__(self):
        return '<Editor>'

    def __init__(self, main_window, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.main_window = main_window
        self.parent = parent
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.util_revealer = Gtk.Revealer()
        self.pack_start(self.util_revealer, False, False, 0)

        self.thesaurus_box = DraftThesaurusBox()
        self.util_revealer.add(self.thesaurus_box)

        self.editor_stack = Gtk.Stack()
        self.pack_start(self.editor_stack, True, True, 0)

        self.statusbar = DraftStatusbar(self)
        self.pack_start(self.statusbar, False, False, 0)

        self.statusbar.connect('word-goal-set', self._on_word_goal_set)
        self.thesaurus_box.connect('cancel-synonym', self._on_cancel_synonym)
        self.thesaurus_box.connect('apply-synonym', self._on_apply_synonym)
        self.connect('key-press-event', self._on_key_press)

    def _prep_view(self, view):
        self.view = view
        self.view.get_style_context().add_class('draft-editor')
        view.connect('thesaurus-requested', self._on_thesaurus_requested)

        self._prep_buffer()

    def _prep_buffer(self, markup='markdown'):
        buffer = self.view.get_buffer()
        buffer.connect('modified-changed', self._on_modified_changed)
        self._on_buffer_changed_id = buffer.connect('changed',
                                                    self._on_buffer_changed)
        self.set_markup(markup)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        # TODO: Add shortcuts to textview
        if (event_and_modifiers and
                event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
            if event.keyval == Gdk.KEY_b:
                self.insert_strong()
            elif event.keyval == Gdk.KEY_i:
                self.insert_emphasis()
            elif event.keyval ==Gdk.KEY_k:
                self.insert_link()

    def _on_word_goal_set(self, widget, goal):
        if self.current_text_data['word_goal'] != goal:
            self.emit('word-goal-set', goal)

    def _on_modified_changed(self, buffer):
        insert = buffer.get_insert()
        self.view.scroll_mark_onscreen(insert)

    def _on_buffer_changed(self, buffer):
        self._write_current_buffer()
        self._update_title_and_subtitle()
        self.statusbar.update_word_count()
        self._set_insert_offset(buffer)
        self._set_last_modified()
        self.emit('view-changed', self.current_text_data)

    def _on_thesaurus_requested(self, widget, word, word_start, word_end):
        self._synonym_word_bounds = (word_start, word_end)
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

    def get_text(self):
        buffer = self.view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, True)
        return text

    def add_tag(self, tag):
        lower_case_tags = [x.lower() for x in self.current_text_data['tags']]
        if tag.lower() in lower_case_tags:
            return

        self.current_text_data['tags'].append(tag)
        self.emit('tags-changed', self.current_text_data['tags'])

    def delete_tag(self, tag):
        lower_case_tags = [x.lower() for x in self.current_text_data['tags']]
        if tag.lower() not in lower_case_tags:
            return

        index = lower_case_tags.index(tag.lower())
        self.current_text_data['tags'].pop(index)
        self.emit('tags-changed', self.current_text_data['tags'])

    def set_markup(self, markup):
        self.markup_type = markup
        if markup == 'markdown':
            self._markup_symbols = MarkdownSymbols()

        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language(markup)
        buffer = self.view.get_buffer()
        buffer.set_language(language)

        if self.current_text_data['markup'] != markup:
            self.emit('markup-changed', markup)

    def switch_view(self, text_data):
        if self._load_in_progress:
            return

        self.util_revealer.set_reveal_child(False)
        self.current_text_data = text_data
        self.emit('text-viewed', self.current_text_data)

        id = str(text_data['id'])
        scrollable = self.editor_stack.get_child_by_name(id)
        if scrollable:
            self.editor_stack.set_visible_child(scrollable)

            view = scrollable.get_child()
            self._prep_view(view)
            self._current_file = self._open_files[id]

            if self.parent.in_preview_mode():
                self.parent.preview_content()

            self.statusbar.update_state()

            return

        view = DraftSourceView()
        self._prep_view(view)

        scrollable = Gtk.ScrolledWindow(None, None)
        scrollable.set_visible(True)
        scrollable.add(view)

        self.editor_stack.add_named(scrollable, id)
        self.editor_stack.set_visible_child(scrollable)

        buffer = view.get_buffer()
        # blocking buffer's `buffer-changed` signal handler while loading
        buffer.handler_block(self._on_buffer_changed_id)

        self._load_in_progress = True
        return buffer

    def load_file(self, gsf, buffer):
        if gsf:
            self._current_file = gsf
            # unblock buffer's `buffer-changed` signal to enable saves
            buffer.handler_unblock(self._on_buffer_changed_id)

            id = self.editor_stack.get_visible_child_name()
            self._open_files[id] = self._current_file
            self._load_in_progress = False

        if self.parent.in_preview_mode():
            self.parent.preview_content()

        self.statusbar.update_state()

    def focus_view(self, scroll_to_insert=False):
        self.view.grab_focus()

        if scroll_to_insert:
            buffer = self.view.get_buffer()
            insert = self._get_insert_for_buffer(buffer)
            GLib.idle_add(self.view.scroll_mark_onscreen, insert)

    def _write_current_buffer(self):
        if not self.view or not self._current_file:
            return

        buffer = self.view.get_buffer()
        file.write_to_source_file_async(self._current_file,
                                        buffer)

    def _get_insert_for_buffer(self, buffer):
        last_edited_position = self.current_text_data['last_edit_position']
        if last_edited_position:
            insert_iter = buffer.get_iter_at_offset(last_edited_position)
            buffer.place_cursor(insert_iter)

        return buffer.get_insert()

    def _set_insert_offset(self, buffer):
        insert_mark = buffer.get_insert()
        insert_iter = buffer.get_iter_at_mark(insert_mark)
        offset = insert_iter.get_offset()

        self.current_text_data['last_edit_position'] = offset

    def _set_last_modified(self):
        datetime = db.get_datetime()
        self.current_text_data['last_modified'] = datetime

    def _update_title_and_subtitle(self):
        content = self.get_text()
        title, subtitle = self._get_title_and_subtitle_for_text(content)

        if title != self.current_text_data['title']:
            self.emit('title-changed', title)

        if subtitle != self.current_text_data['subtitle']:
            self.emit('subtitle-changed', subtitle)

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
