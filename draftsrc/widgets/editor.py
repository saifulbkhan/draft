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

from gi.repository import Gtk, GObject, GtkSource, Gdk, GLib, Pango

from draftsrc import file
from draftsrc import db
from draftsrc.widgets.statusbar import DraftStatusbar

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

    def __repr__(self):
        return '<Editor>'

    def __init__(self, main_window, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.main_window = main_window
        self.parent = parent
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.editor_stack = Gtk.Stack()
        self.pack_start(self.editor_stack, True, True, 0)

        self.statusbar = DraftStatusbar(self)
        self.pack_start(self.statusbar, False, False, 0)

        self.statusbar.connect('word-goal-set', self._on_word_goal_set)
        self.connect('key-press-event', self._on_key_press)

    def _prep_view(self, view):
        self.view = view

        self.view.set_visible(True)
        self.view.set_pixels_above_lines(6)
        self.view.set_pixels_below_lines(6)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.view.set_left_margin(24)
        self.view.set_right_margin(24)
        self.view.set_top_margin(10)
        self.view.scroll_offset = 3
        self.view.overscroll_num_lines = 3
        self.view.get_style_context().add_class('draft-editor')

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
        if event_and_modifiers:
            if (event.keyval == Gdk.KEY_s
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                pass

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

    def get_text(self):
        buffer = self.view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)
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
        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language(markup)
        buffer = self.view.get_buffer()
        buffer.set_language(language)
        if self.current_text_data['markup'] != markup:
            self.emit('markup-changed', markup)

    def switch_view(self, text_data):
        if self._load_in_progress:
            return

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

        view = DraftTextView()
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


class DraftTextView(GtkSource.View):
    __gtype_name__ = 'DraftTextView'

    _context_menu = None
    scroll_duration = 150

    def __repr__(self):
        return '<DraftTextView>'

    def __init__(self):
        GtkSource.View.__init__(self)
        self.connect('event', self._on_event)

        self.cached_char_height = 0
        self.cached_char_width = 0
        self.scroll_offset = 0

        # Variables for scroll animation setup
        self._tick_id = 0
        self._source = 0.0
        self._target = 0.0
        self._start_time = None
        self._end_time = None

    def get_visible_rect(self):
        area = GtkSource.View.get_visible_rect(self)
        area.y += self.get_top_margin()

        # If we don't have valid line height, not much we can do now. We can
        # just adjust things later once it becomes available.
        if self.cached_char_height:
            visible_lines = int(area.height / self.cached_char_height)
            max_scroll_offset = (visible_lines - 1)/ 2
            scroll_offset = min(self.scroll_offset, max_scroll_offset)
            scroll_offset_height = self.cached_char_height * scroll_offset

            area.y += scroll_offset_height
            area.height -= (2* scroll_offset_height)

            # If we have an even number of visible lines and scrolloffset is
            # less than our desired scrolloffset, we need to remove an extra
            # line so we don't have two visible lines.
            if scroll_offset < self.scroll_offset and (visible_lines % 2) == 0:
                area.height -= self.cached_char_height

            # Use a multiple of the line height so we don't jump around when
            # focusing the last line (due to Y2 not fitting in the visible
            # area).
            area.height = int(area.height / self.cached_char_height) \
                          * self.cached_char_height
        return area

    def scroll_to_iter(self, text_iter, within_margin,
                       use_align, xalign, yalign):
        buffer = self.get_buffer()

        hadj = self.get_hadjustment()
        vadj = self.get_vadjustment()

        rect = self.get_iter_location(text_iter)
        screen = self.get_visible_rect()

        current_x_scroll = screen.x
        current_y_scroll = screen.y

        screen_x_offset = screen.width * within_margin
        screen_y_offset = screen.height * within_margin

        screen.x += screen_x_offset
        screen.y += screen_y_offset
        screen.width -= screen_x_offset * 2
        screen.height -= screen_y_offset * 2

        if screen.width < 1:
            screen.width = 1
        if screen.height < 1:
            screen.height = 1

        # The -1 here ensures that we leave enough space to draw the cursor
        # when this function is used for horizontal scrolling.
        screen_right = screen.x + screen.width - 1
        screen_bottom = screen.y + screen.height

        # The alignment affects the point in the target character that we
        # choose to align. If we're doing right/bottom alignment, we align
        # the right/bottom edge of the character the mark is at; if we're
        # doing left/top we align the left/top edge of the character; if
        # we're doing center alignment we align the center of the
        # character.

        # Vertical alignment
        scroll_dest = current_y_scroll
        yvalue = 0
        if use_align:
            scroll_dest = rect.y + (rect.height * yalign) - (screen.height * yalign);

            # if scroll_dest < screen.y, we move a negative increment (up),
            # else a positive increment (down)
            yvalue = scroll_dest - screen.y + screen_y_offset
        else:
            if rect.y < screen.y:
                scroll_dest = rect.y
                yvalue = scroll_dest - screen.y - screen_y_offset
            elif (rect.y + rect.height) > screen_bottom:
                scroll_dest = rect.y + rect.height
                yvalue = scroll_dest - screen_bottom + screen_y_offset
        yvalue += current_y_scroll

        # Scroll offset adjustment
        if self.cached_char_height:
            true_height = GtkSource.View.get_visible_rect(self).height
            visible_lines = int(true_height / self.cached_char_height)
            max_scroll_offset = (visible_lines - 1)/ 2
            scroll_offset = min(self.scroll_offset, max_scroll_offset)
            scroll_offset_height = self.cached_char_height * scroll_offset

            if scroll_offset_height > 0:
                if rect.y - scroll_offset_height < yvalue:
                    yvalue -= (scroll_offset_height - (rect.y - yvalue))
                elif self._gdk_rectangle_y2(rect) + scroll_offset_height > yvalue + screen.height:
                    yvalue += (self._gdk_rectangle_y2(rect) + scroll_offset_height) - (yvalue + true_height)

        # Horizontal alignment
        scroll_dest = current_x_scroll
        xvalue = 0
        if use_align:
            scroll_dest = rect.x + (rect.width * xalign) - (screen.width * xalign)

            # if scroll_dest < screen.y, we move a negative increment (left),
            # else a positive increment (right)
            xvalue = scroll_dest - screen.x + screen_x_offset
        else:
            if rect.x < screen.x:
                scroll_dest = rect.x
                xvalue = scroll_dest - screen.x - screen_x_offset
            elif (rect.x + rect.width) > screen_right:
                scroll_dest = rect.x + rect.width
                xvalue = scroll_dest - screen_right + screen_x_offset
        xvalue += current_x_scroll

        hadj.set_value(xvalue)
        self.set_value_alt(vadj, yvalue, True)

    # TODO: Separate from this class
    def _gdk_rectangle_y2(self, rect):
        return rect.y + rect.height

    # TODO: Separate from this class
    def _gdk_rectangle_x2(self, rect):
        return rect.x + rect.width

    def _gdk_rectangle_contains(self, a, b):
        return a.x <= b.x and\
               a.x + int(a.width) >= b.x + int(b.width) and\
               a.y <= b.y and\
               a.y + int(a.height) >= b.y + int(b.height)

    def _begin_updating(self, adjustment, clock):
        if not self._tick_id:
            self._tick_id = clock.connect("update",
                                               self._on_frame_clock_update,
                                               adjustment)
            clock.begin_updating()

    def _end_updating(self, adjustment, clock):
        if self._tick_id:
            clock.disconnect(self._tick_id)
            self._tick_id = 0
            clock.end_updating()

    def _on_frame_clock_update (self, clock, adjustment):
        now = clock.get_frame_time()

        # From clutter-easing.c, based on Robert Penner's
        # infamous easing equations, MIT license.
        def ease_out_cubic(t):
            p = t - 1
            return p * p * p + 1

        if now < self._end_time:
            t = (now - self._start_time) / (self._end_time - self._start_time)
            t = ease_out_cubic(t)
            adjustment.set_value(self._source + t * (self._target - self._source))
        else:
            adjustment.set_value(self._target)
            self._end_updating(adjustment, clock)

    def set_value_alt(self, adjustment, value, animate=False):
        value = min(value, adjustment.get_upper() - adjustment.get_page_size())
        value = max(value, adjustment.get_lower())
        clock = self.get_frame_clock()

        if self.scroll_duration and animate and clock:
            if self._tick_id and self._target == value:
                return

            self._source = adjustment.get_value()
            self._target = value
            self._start_time = clock.get_frame_time()
            self._end_time = self._start_time + 1000 * self.scroll_duration
            self._begin_updating(adjustment, clock)
        else:
            self._end_updating(adjustment, clock)
            adjustment.set_value(value)

    def scroll_mark_onscreen(self, mark):
        visible_rect = self.get_visible_rect()
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        mark_rect = self.get_iter_location(text_iter)

        if not self._gdk_rectangle_contains(visible_rect, mark_rect):
            yalign = 1.0
            if mark_rect.y < visible_rect.y:
                yalign = 0.0
            self.scroll_to_mark(mark, 0.0, True, 0.0, yalign)

    def scroll_to_mark(self, mark, within_margin,
                       use_align, xalign, yalign):
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        self.scroll_to_iter(text_iter, within_margin, use_align, xalign, yalign)

    def refresh_overscroll(self):
        height = self.get_allocated_height()
        new_margin = self.overscroll_num_lines * self.cached_char_height

        if new_margin < 0:
            new_margin = height + new_margin
        new_margin = min(max(new_margin, 0), height)

        self.set_bottom_margin(new_margin)

    def do_move_cursor(self, step, count, extend_selection):
        GtkSource.View.do_move_cursor(self, step, count, extend_selection)
        insert = self.get_buffer().get_insert()
        self.scroll_mark_onscreen(insert)

    def do_style_updated(self):
        GtkSource.View.do_style_updated(self)

        context = self.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text('X', 1)
        self.cached_char_width, self.cached_char_height = layout.get_pixel_size()
        self.cached_char_height += self.get_pixels_above_lines() +\
                                   self.get_pixels_below_lines()

    def do_size_allocate(self, allocation):
        GtkSource.View.do_size_allocate(self, allocation)
        self.refresh_overscroll()

    def _on_event(self, widget, event):
        key_pressed, key = event.get_keyval()
        menu_requested = (key_pressed
                          and (key == Gdk.KEY_Menu
                               or key == Gdk.KEY_MenuPB
                               or key == Gdk.KEY_MenuKB))
        if event.triggers_context_menu() or menu_requested:
            self._popup_context_menu(event)
            return True

    def _popup_context_menu(self, event):
        clipboard = self.get_clipboard(Gdk.SELECTION_CLIPBOARD)
        clipboard.wait_for_text()
        target = Gdk.Atom.intern_static_string("TARGETS")
        clipboard.request_contents(target, self._popup_targets_recieved, event)

    def _popup_targets_recieved(self, clipboard, selection_data, user_data):
        self._context_menu = Gtk.PopoverMenu()
        self._context_menu.set_relative_to(self)

        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._context_menu.add(item_box)

        buffer = self.get_buffer()
        editable = self.get_editable()
        event = user_data

        have_selection = False
        sel_start = None
        sel_end = None
        selection = buffer.get_selection_bounds()
        if selection:
            sel_start, sel_end = selection
            have_selection = True

        text_iter = buffer.get_iter_at_mark(buffer.get_insert())

        can_insert = text_iter.can_insert(editable)
        can_paste = selection_data.targets_include_text()

        def range_contains_editable_text(start, end, default_editability):
            iter = start
            while iter.compare(end) < 0:
                if iter.editable(default_editability):
                    return True

                iter.forward_to_tag_toggle(None)

            return False

        def on_cut(widget):
            self.emit('cut-clipboard')

        def on_copy(widget):
            self.emit('copy-clipboard')

        def on_paste(widget):
            self.emit('paste-clipboard')

        cut_button = Gtk.ModelButton()
        cut_button.set_label(_("Cut"))
        cut_button.connect('clicked', on_cut)
        cut_button.set_sensitive(have_selection
                                 and range_contains_editable_text(sel_start,
                                                                  sel_end,
                                                                  editable))

        copy_button = Gtk.ModelButton()
        copy_button.set_label(_("Copy"))
        copy_button.connect('clicked', on_copy)
        copy_button.set_sensitive(have_selection)

        paste_button = Gtk.ModelButton()
        paste_button.set_label(_("Paste"))
        paste_button.connect('clicked', on_paste)
        paste_button.set_sensitive(can_insert and can_paste)

        for button in [cut_button, copy_button, paste_button]:
            item_box.add(button)
            label = button.get_child()
            label.set_halign(Gtk.Align.START)

        item_box.show_all()
        item_box.get_style_context().add_class("draft-menu-box")

        if event.triggers_context_menu():
            __, x, y = event.get_coords()
            rect = self.get_allocation()
            rect.x, rect.y, rect.height, rect.width = x, y, 0, 0
            self._context_menu.set_pointing_to(rect)
        else:
            visible = GtkSource.View.get_visible_rect(self)
            rect = self.get_iter_location(text_iter)
            if self._gdk_rectangle_contains(visible, rect):
                rect.x, rect.y = self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,
                                                              rect.x, rect.y)
                self._context_menu.set_pointing_to(rect)
            else:
                visible = self.get_allocation()
                rect.x = int((visible.x + visible.width) / 2)
                rect.y = int((visible.y + visible.height) / 2)
                rect.width, rect.height = 0, 0
                self._context_menu.set_pointing_to(rect)

        self._context_menu.set_position(Gtk.PositionType.BOTTOM)
        self._context_menu.popup()
