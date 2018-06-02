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

import cairo
from math import pi as PI
from gettext import gettext as _

import gi
gi.require_version('GtkSource', '3.0')
gi.require_version('Gspell', '1')

from gi.repository import Gtk, GObject, GtkSource, Gdk, Pango, Gspell, Gio

from draftsrc.widgets.editor.sourcebuffer import DraftSourceBuffer

DEFAULT_SCROLL_OFFSET, DEFAULT_NUM_OVERSCROLL = 3, 3
DEFAULT_LEFT_MARGIN, DEFAULT_RIGHT_MARGIN = 24, 24


class TypewriterModeType(object):
    UPPER = 1
    CENTER = 2
    LOWER = 3


class DraftSourceView(GtkSource.View):
    __gtype_name__ = 'DraftSourceView'

    __gsignals__ = {
        'thesaurus-requested': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_STRING,
                                 GObject.TYPE_PYOBJECT,
                                 GObject.TYPE_PYOBJECT))
    }

    _context_menu = None
    _url_change_id = None
    _title_change_id = None
    _hint_label = ""
    _hint_label_margin = 12
    _typewriter_mode = False
    _typewriter_mode_type = None
    scroll_duration = 150
    free_width_limit = 800
    scroll_offset = DEFAULT_SCROLL_OFFSET
    overscroll_num_lines = DEFAULT_NUM_OVERSCROLL
    _calculated_top_margin = 24
    _calculated_bottom_margin = 24

    def __repr__(self):
        return '<DraftSourceView>'

    def __init__(self):
        GtkSource.View.__init__(self)
        self.set_buffer(DraftSourceBuffer())

        self._spell_checker = Gspell.Checker()
        buffer = self.get_buffer()
        gspell_buffer = Gspell.TextBuffer.get_from_gtk_text_buffer(buffer)
        gspell_buffer.set_spell_checker(self._spell_checker)
        gspell_view = Gspell.TextView.get_from_gtk_text_view(self)
        gspell_view.set_inline_spell_checking(True)

        # TODO: Disabling this for now. These elements should not be created
        #       for every SourceView. Make DraftEditor own them.
        # builder = Gtk.Builder()
        # builder.add_from_resource('/org/gnome/Draft/editor.ui')

        # self._link_editor = builder.get_object('link_editor')
        # self._url_entry = builder.get_object('url_entry')
        # self._title_entry = builder.get_object('title_entry')
        # self._img_editor = builder.get_object('img_editor')
        # self._img_url_entry = builder.get_object('img_url_entry')
        # self._img_title_entry = builder.get_object('img_title_entry')
        # self._browse_images_button = builder.get_object('browse_images_button')
        # self._hint_window = builder.get_object('hint_window')

        # self._link_editor.set_relative_to(self)
        # self._img_editor.set_relative_to(self)

        # screen = self._hint_window.get_screen()
        # visual = screen.get_rgba_visual()
        # if visual is not None and screen.is_composited():
        #     self._hint_window.set_visual(visual)
        # self._hint_window.set_app_paintable(True)

        self.connect('event', self._on_event)
        self.connect('key-press-event', self._on_key_press)
        self.connect('focus-in-event', self._on_focus_in)
        self.connect('focus-out-event', self._on_focus_out)

        # self._link_editor.connect('closed', self._on_link_editor_closed)
        # self._img_editor.connect('closed', self._on_link_editor_closed)
        # self._browse_images_button.connect('clicked', self._on_browse_images)
        # self._hint_window.connect('draw', self._on_hint_window_draw)

        self.cached_char_height = 0
        self.cached_char_width = 0
        self.set_has_tooltip(True)

        # visual margins and offsets
        self.set_visible(True)
        self.set_pixels_above_lines(3)
        self.set_pixels_below_lines(3)
        self.set_pixels_inside_wrap(6)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_left_margin(DEFAULT_LEFT_MARGIN)
        self.set_right_margin(DEFAULT_RIGHT_MARGIN)
        self.set_top_margin(self._calculated_top_margin)
        self.set_bottom_margin(self._calculated_bottom_margin)

        # formatting specific options
        self.set_auto_indent(True)
        self.set_indent_on_tab(True)
        self.set_insert_spaces_instead_of_tabs(True)
        self.set_indent_width(2)
        self.set_smart_backspace(True)
        self.set_highlight_current_line(True)

        # Variables for scroll animation setup
        self._tick_id = 0
        self._source = 0.0
        self._target = 0.0
        self._start_time = None
        self._end_time = None

    def get_visible_rect(self):
        area = GtkSource.View.get_visible_rect(self)
        self.refresh_overscroll()

        # If we don't have valid line height, not much we can do now. We can
        # just adjust things later once it becomes available.
        if self.cached_char_height:
            if self._typewriter_mode:
                area.height = self.cached_char_height
                return area

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
                       use_align, xalign, yalign, animate=True):
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
            scroll_dest = rect.y + (rect.height * yalign) - (screen.height * yalign)

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
            if self._typewriter_mode:
                scroll_offset = self.scroll_offset
                scroll_offset_height = self.cached_char_height * scroll_offset
                if scroll_offset_height > 0:
                    if rect.y - scroll_offset_height < yvalue:
                        yvalue -= (scroll_offset_height - (rect.y - yvalue))
                    elif self._gdk_rectangle_y2(rect) + scroll_offset_height > yvalue + screen.height:
                        yvalue += (self._gdk_rectangle_y2(rect) + scroll_offset_height) - (yvalue + true_height)
            else:
                visible_lines = int(true_height / self.cached_char_height)
                max_scroll_offset = (visible_lines - 1)/ 2
                scroll_offset = min(self.scroll_offset, max_scroll_offset)
                scroll_offset_height = self.cached_char_height * scroll_offset
                if scroll_offset_height > 0:
                    if rect.y - scroll_offset_height < yvalue:
                        yvalue -= (scroll_offset_height - (rect.y - yvalue)) - self.cached_char_height
                    elif self._gdk_rectangle_y2(rect) + scroll_offset_height > yvalue + screen.height:
                        yvalue += (self._gdk_rectangle_y2(rect) + scroll_offset_height + self.cached_char_height) - (yvalue + true_height)

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
        self.set_value_alt(vadj, yvalue, animate)

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

    def scroll_mark_onscreen(self, mark, animate=True):
        visible_rect = self.get_visible_rect()
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        mark_rect = self.get_iter_location(text_iter)

        if not self._gdk_rectangle_contains(visible_rect, mark_rect):
            yalign = 1.0
            if mark_rect.y < visible_rect.y:
                yalign = 0.0
            self.scroll_to_mark(mark, 0.0, True, 0.0, yalign, animate)

    def scroll_to_mark(self, mark, within_margin,
                       use_align, xalign, yalign, animate=True):
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        self.scroll_to_iter(text_iter, within_margin, use_align,
                            xalign, yalign, animate)

    def refresh_overscroll(self):
        height = self.get_allocated_height()
        new_margin = self.overscroll_num_lines * self.cached_char_height

        if new_margin < 0:
            new_margin = height + new_margin
        new_margin = min(max(new_margin, 0), height)

        if self._typewriter_mode:
            top_margin = new_margin
            bottom_margin = height - new_margin

            # add overscroll margins only if the insertion cursor is near the
            # edges of the document
            buffer = self.get_buffer()
            insert = buffer.get_iter_at_mark(buffer.get_insert())
            loc = self.get_iter_location(insert)
            end = buffer.get_end_iter()
            end_loc = self.get_iter_location(end)
            if loc.y <= top_margin:
                self.set_top_margin(top_margin - loc.y + self._calculated_top_margin)
            else:
                self.set_top_margin(self._calculated_top_margin)
            if self._gdk_rectangle_y2(end_loc) - self._gdk_rectangle_y2(loc) <= bottom_margin:
                self.set_bottom_margin(bottom_margin -\
                                       (self._gdk_rectangle_y2(end_loc) -\
                                        self._gdk_rectangle_y2(loc)))
            else:
                self.set_bottom_margin(self._calculated_bottom_margin)

            # need to do this for margins to properly update with blank space
            GtkSource.View.do_style_updated(self)
        else:
            self.set_bottom_margin(new_margin)

    def do_move_cursor(self, step, count, extend_selection):
        GtkSource.View.do_move_cursor(self, step, count, extend_selection)
        buffer = self.get_buffer()
        insert_mark = buffer.get_insert()
        if self._typewriter_mode:
            self.scroll_mark_onscreen(insert_mark, animate=False)
        else:
            self.scroll_mark_onscreen(insert_mark)

        # TODO: Disabling this until link editor is stable.
        # editable = self.get_editable()
        # insert = buffer.get_iter_at_mark(insert_mark)

        # if count > 0:
        #     insert.forward_char()

        # link_start = insert.copy()
        # link_end = insert.copy()
        # if not insert.can_insert(editable):
        #     start = buffer.get_start_iter()
        #     end = buffer.get_end_iter()
        #     while not link_end.can_insert(editable) and link_end.compare(end) < 0:
        #         link_end.forward_char()
        #     while not link_start.can_insert(editable) and link_start.compare(start) > 0:
        #         link_start.backward_char()

        #     # one final forward/backward towards regular text
        #     link_start.backward_char()

        #     if extend_selection:
        #         sel_start, sel_end = buffer.get_selection_bounds()
        #         if count > 0:
        #             buffer.select_range(link_end, sel_start)
        #         else:
        #             buffer.select_range(link_start, sel_end)
        #     else:
        #         if count > 0:
        #             buffer.place_cursor(link_end)
        #         else:
        #             buffer.place_cursor(link_start)

        # self._show_hint_window()

    def do_backspace(self):
        # TODO: Disabling this until link editor is stable.
        # buffer = self.get_buffer()
        # insert_mark = buffer.get_insert()
        # insert = buffer.get_iter_at_mark(insert_mark)
        # insert.backward_char()
        # editable = self.get_editable()

        # if not insert.can_insert(editable):
        #     start = buffer.get_start_iter()
        #     while not insert.can_insert(editable) and insert.compare(start) > 0:
        #         insert.backward_char()
        #     buffer.place_cursor(insert)

        GtkSource.View.do_backspace(self)

    def do_style_updated(self):
        GtkSource.View.do_style_updated(self)

        context = self.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text('X', 1)
        self.cached_char_width, self.cached_char_height = layout.get_pixel_size()
        self.cached_char_height += self.get_pixels_above_lines() +\
                                   self.get_pixels_below_lines()
        self._calculated_top_margin = self._calculated_bottom_margin = self.cached_char_height
        self.set_top_margin(self._calculated_top_margin)
        self.set_bottom_margin(self._calculated_bottom_margin)
        if not self._typewriter_mode:
            self.set_top_margin(self._calculated_top_margin)

    def do_size_allocate(self, allocation):
        GtkSource.View.do_size_allocate(self, allocation)
        if allocation.width > self.free_width_limit:
            extra_space = allocation.width - self.free_width_limit

            # put 90% of extra space as padding divided among the two
            # horizontal edges
            horizontal_offset = (extra_space / 2) * 0.9
            self.set_left_margin(DEFAULT_LEFT_MARGIN + horizontal_offset)
            self.set_right_margin(DEFAULT_RIGHT_MARGIN + horizontal_offset)
        else:
            self.set_left_margin(DEFAULT_LEFT_MARGIN)
            self.set_right_margin(DEFAULT_RIGHT_MARGIN)

        if self._typewriter_mode:
            area = GtkSource.View.get_visible_rect(self)
            if self.cached_char_height:
                visible_lines = int(area.height / self.cached_char_height) - 1
                if self._typewriter_mode_type == TypewriterModeType.UPPER:
                    self.scroll_offset = (visible_lines - 1) / 4
                    self.overscroll_num_lines = (visible_lines - 1) / 4
                elif self._typewriter_mode_type == TypewriterModeType.LOWER:
                    self.scroll_offset = (visible_lines - 1) * 3 / 4
                    self.overscroll_num_lines = (visible_lines - 1) * 3 / 4
                else:
                    self.scroll_offset = (visible_lines - 1) / 2
                    self.overscroll_num_lines = self.scroll_offset
        self.refresh_overscroll()

    def _on_event(self, widget, event):
        key_pressed, key = event.get_keyval()
        menu_requested = (key_pressed
                          and (key == Gdk.KEY_Menu
                               or key == Gdk.KEY_MenuPB
                               or key == Gdk.KEY_MenuKB))
        if event.triggers_context_menu() or menu_requested:
            self._popup_context_menu(event, menu_requested)
            return True

    def _on_key_press(self, widget, event):
        key = event.keyval
        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if modifiers:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK
            alt_mask = Gdk.ModifierType.MOD1_MASK

            # TODO: Hiding this until link editing/hiding is more stable.
            # if ((key == Gdk.KEY_Return
            #         or key == Gdk.KEY_KP_Enter
            #         or key == Gdk.KEY_ISO_Enter)
            #         and modifiers == control_mask):
            #     buffer = self.get_buffer()
            #     on_link, is_image, start, end = buffer.cursor_is_on_link()
            #     if on_link:
            #         self._popup_link_editor(start, end, is_image)
            pass

    def _popup_context_menu(self, event, menu_requested):
        clipboard = self.get_clipboard(Gdk.SELECTION_CLIPBOARD)
        clipboard.wait_for_text()
        target = Gdk.Atom.intern_static_string("TARGETS")
        clipboard.request_contents(target,
                                   self._popup_targets_recieved,
                                   (event, menu_requested))

    def _popup_targets_recieved(self, clipboard, selection_data, user_data):
        self._context_menu = Gtk.PopoverMenu()
        self._context_menu.set_relative_to(self)

        item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._context_menu.add(item_box)

        buffer = self.get_buffer()
        editable = self.get_editable()
        event, key_press_menu_request = user_data

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
            iter = start.copy()
            while iter.compare(end) < 0:
                if iter.editable(default_editability):
                    return True

                iter.forward_to_tag_toggle(None)

            return False

        def only_one_selected_word():
            # return True when nothing is selected because cursor would be
            # within or on the fringes of a word. Whether if its actually on
            # a word needs to be checked separately
            if not have_selection:
                return True

            selected_text = buffer.get_text(sel_start, sel_end, True)
            if len(selected_text.split()) > 1:
                return False

            return True

        def spelling_suggestions_needed():
            if key_press_menu_request:
                insert_mark = buffer.get_insert()
                insert = buffer.get_iter_at_mark(insert_mark)
                word, word_start, word_end = buffer.get_word_at_iter(insert)
                if word:
                    correctly_spelled = self._spell_checker.check_word(word, -1)
                    if not correctly_spelled:
                        return True, word, word_start, word_end
                    else:
                        return False, word, word_start, word_end

                return False, None, None, None

            textiter = self._get_iter_at_event(event)
            if textiter:
                word, word_start, word_end = buffer.get_word_at_iter(textiter)
                if word:
                    correctly_spelled = self._spell_checker.check_word(word, -1)
                    if not correctly_spelled:
                        return True, word, word_start, word_end
                    else:
                        return False, word, word_start, word_end

            return False, None, None, None

        suggestions_needed, word, word_start, word_end = spelling_suggestions_needed()

        def on_cut(widget):
            self.emit('cut-clipboard')

        def on_copy(widget):
            self.emit('copy-clipboard')

        def on_paste(widget):
            self.emit('paste-clipboard')

        def on_select_all(widget):
            self.emit('select-all', True)

        def on_undo(widget):
            self.emit('undo')

        def on_redo(widget):
            self.emit('redo')

        def on_suggestion_selected(widget):
            label = widget.get_child()
            correct_spelling = label.get_label()
            if word_start and word_end:
                buffer.replace_text_between(word_start,
                                            word_end,
                                            correct_spelling)
                buffer.place_cursor(word_start)

        def on_add_to_dictionary(widget):
            self._spell_checker.add_word_to_personal(word, -1)

        def on_ignore(widget):
            self._spell_checker.add_word_to_session(word, -1)

        def on_reveal_thesaurus(widget):
            self.emit('thesaurus-requested', word, word_start, word_end)

        menu_items = []
        if (suggestions_needed and
                range_contains_editable_text(word_start, word_end, self.get_editable())):
            suggestions = self._spell_checker.get_suggestions(word, -1)
            suggestions = suggestions[0:3]
            for suggested in suggestions:
                suggestion_button = Gtk.ModelButton()
                suggestion_button.set_label(suggested)
                suggestion_button.connect('clicked', on_suggestion_selected)
                menu_items.append(suggestion_button)

            # add a separator only if there is a suggestion section
            if suggestions:
                separator_0 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                menu_items.append(separator_0)

            add_to_dictionary_button = Gtk.ModelButton()
            add_to_dictionary_button.set_label(_("Add “%s” to dictionary") % word)
            add_to_dictionary_button.connect('clicked', on_add_to_dictionary)
            menu_items.append(add_to_dictionary_button)

            ignore_button = Gtk.ModelButton()
            ignore_button.set_label(_("Ignore"))
            ignore_button.connect('clicked', on_ignore)
            menu_items.append(ignore_button)

            separator_0 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            menu_items.append(separator_0)
        elif (word and only_one_selected_word() and
                range_contains_editable_text(word_start, word_end, self.get_editable())):
            # if spelt correctly provide option to look for synonyms
            reveal_thesaurus_button = Gtk.ModelButton()
            reveal_thesaurus_button.set_label(_("Find synonyms for “%s”") % word)
            reveal_thesaurus_button.connect('clicked', on_reveal_thesaurus)
            menu_items.append(reveal_thesaurus_button)

            separator_0 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            menu_items.append(separator_0)

        undo_button = Gtk.ModelButton()
        undo_button.set_label(_("Undo"))
        undo_button.connect('clicked', on_undo)
        undo_button.set_sensitive(buffer.can_undo())
        menu_items.append(undo_button)

        redo_button = Gtk.ModelButton()
        redo_button.set_label(_("Redo"))
        redo_button.connect('clicked', on_redo)
        redo_button.set_sensitive(buffer.can_redo())
        menu_items.append(redo_button)

        separator_1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        menu_items.append(separator_1)

        cut_button = Gtk.ModelButton()
        cut_button.set_label(_("Cut"))
        cut_button.connect('clicked', on_cut)
        cut_button.set_sensitive(have_selection
                                 and range_contains_editable_text(sel_start,
                                                                  sel_end,
                                                                  editable))
        menu_items.append(cut_button)

        copy_button = Gtk.ModelButton()
        copy_button.set_label(_("Copy"))
        copy_button.connect('clicked', on_copy)
        copy_button.set_sensitive(have_selection)
        menu_items.append(copy_button)

        paste_button = Gtk.ModelButton()
        paste_button.set_label(_("Paste"))
        paste_button.connect('clicked', on_paste)
        paste_button.set_sensitive(can_insert and can_paste)
        menu_items.append(paste_button)

        separator_2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        menu_items.append(separator_2)

        select_all_button = Gtk.ModelButton()
        select_all_button.set_label(_("Select All"))
        select_all_button.connect('clicked', on_select_all)
        select_all_button.set_sensitive(buffer.get_char_count() > 0)
        menu_items.append(select_all_button)

        for item in menu_items:
            item_box.add(item)
            if isinstance(item, Gtk.Button):
                label = item.get_child()
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

    def _popup_link_editor(self, start, end, is_image=False, backward=False):
        self.set_editable(False)
        buffer = self.get_buffer()
        bounds = buffer.obtain_link_bounds(start, end, backward)
        url_iters = bounds.get('url')
        if not url_iters:
            self.set_editable(True)
            return

        url_start, url_end = url_iters
        url_mark_start = buffer.create_mark(None, url_start, False)
        url_mark_end = buffer.create_mark(None, url_end, False)

        link_editor = self._link_editor
        url_entry = self._url_entry
        title_entry = self._title_entry
        if is_image:
            link_editor = self._img_editor
            url_entry = self._img_url_entry
            title_entry = self._img_title_entry

        url_entry.set_text("")
        title_entry.set_text("")

        title_delimiter = ""
        # make iterators enter within brackets
        url_start.forward_char()
        url_end.backward_char()
        url_string = buffer.get_slice(url_start, url_end, True)
        url_string = url_string.strip()

        idx = -1
        if url_string.endswith('"'):
            idx = url_string.rfind('"', 0, -1)
        elif url_string.endswith("'"):
            idx = url_string.rfind("'", 0, -1)

        if idx != -1:
            url = url_string[:idx]
            title = url_string[idx+1:-1]
            url_entry.set_text(url.strip())
            title_entry.set_text(title)
        else:
            url_entry.set_text(url_string)

        def clear_url_space():
            start = buffer.get_iter_at_mark(url_mark_start)
            end = buffer.get_iter_at_mark(url_mark_end)
            start.forward_char()
            end.backward_char()
            buffer.delete(start, end)

        def insert_into_url_space(string):
            start = buffer.get_iter_at_mark(url_mark_start)
            start.forward_char()
            buffer.insert(start, string)

        def on_url_changed(widget, user_data=None):
            url = url_entry.get_text()
            url = url.strip()
            title = title_entry.get_text()
            title = title.strip()
            clear_url_space()
            if title:
                url += ' "' + title + '"'
            insert_into_url_space(url)

        def on_activated(widget, user_data=None):
            link_editor.popdown()

        self._url_change_id = url_entry.connect('changed', on_url_changed)
        self._title_change_id = title_entry.connect('changed', on_url_changed)
        url_entry.connect('activate', on_activated)
        title_entry.connect('activate', on_activated)

        insert = buffer.get_iter_at_mark(buffer.get_insert())
        insert_rect = self.get_iter_location(insert)
        x, y = self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,
                                            insert_rect.x,
                                            insert_rect.y)
        insert_rect.x, insert_rect.y = x, y
        link_editor.set_pointing_to(insert_rect)

        link_editor.popup()

    def _on_link_editor_closed(self, widget):
        url_entry = self._url_entry
        title_entry = self._title_entry
        if widget == self._img_editor:
            url_entry = self._img_url_entry
            title_entry = self._img_title_entry
        url_entry.disconnect(self._url_change_id)
        title_entry.disconnect(self._title_change_id)
        self.set_editable(True)

    def _on_browse_images(self, widget):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Draft/editor.ui')
        image_chooser_dialog = builder.get_object('image_chooser_dialog')
        cancel_browse_button = builder.get_object('cancel_browse_button')
        open_image_button = builder.get_object('open_image_button')

        def on_cancel_browse(widget):
            image_chooser_dialog.response(Gtk.ResponseType.DELETE_EVENT)

        def on_open_image(widget):
            image_chooser_dialog.response(Gtk.ResponseType.ACCEPT)

        def on_dialog_selection_changed(widget):
            uri = image_chooser_dialog.get_uri()
            if uri is None:
                open_image_button.set_sensitive(False)
            else:
                open_image_button.set_sensitive(True)

        cancel_browse_button.connect('clicked', on_cancel_browse)
        open_image_button.connect('clicked', on_open_image)
        image_chooser_dialog.connect('selection-changed',
                                     on_dialog_selection_changed)
        image_chooser_dialog.connect('file-activated', on_open_image)

        image_chooser_dialog.set_transient_for(self.get_toplevel())
        response = image_chooser_dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            f = image_chooser_dialog.get_file()
            if f:
                self._img_url_entry.set_text(f.get_uri())
                name = f.get_basename()
                dot = name.rfind('.')
                if dot != -1:
                    name = name[:dot]
                self._img_title_entry.set_text(name)

        image_chooser_dialog.destroy()

    def _show_hint_window(self):
        buffer = self.get_buffer()
        on_link, is_image, start, end = buffer.cursor_is_on_link()
        if on_link:
            self._hint_label = _("Ctrl+Enter to Edit Link")
            if is_image:
                self._hint_label = _("Ctrl+Enter to Edit Image")
            self._hint_window.set_visible(True)
            insert = buffer.get_iter_at_mark(buffer.get_insert())
            rect = self.get_iter_location(insert)
            x, y = self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,
                                                rect.x,
                                                rect.y)

            toplevel = self.get_toplevel()
            res = self.translate_coordinates(toplevel, x, y)
            if res:
                x, y = res

            window = toplevel.get_window()
            off_x, off_y = window.get_position()

            alloc = self._hint_window.get_allocation()
            width_offset = (alloc.width / 2) - (self._hint_label_margin * 2)
            height_offset = rect.height

            self._hint_window.move(x + off_x - width_offset,
                                   y + off_y + height_offset)
        else:
            self._hint_window.set_visible(False)

    def _on_hint_window_draw(self, widget, ctx):
        style_ctx = self._hint_window.get_style_context()
        font = style_ctx.get_font(style_ctx.get_state())
        border_success, border_color = style_ctx.lookup_color('borders')
        bg_success, bg_color = style_ctx.lookup_color('theme_bg_color')
        fg_success, fg_color = style_ctx.lookup_color('theme_fg_color')

        font_size = int((font.get_size() / Pango.SCALE) * 96 / 72)
        ctx.set_font_size(font_size)
        font_family = font.get_family()
        ctx.select_font_face(font_family,
                             cairo.FontSlant.NORMAL,
                             cairo.FontWeight.NORMAL)
        offset = self._hint_label_margin * 96 / 72
        text = self._hint_label
        extents = ctx.text_extents(text)

        ctx.set_source_rgb(border_color.red,
                           border_color.green,
                           border_color.blue)
        self._draw_rounded_rectangle(ctx, 0, 0,
                                     extents.width + (offset * 2),
                                     extents.height + (offset * 2),
                                     3)
        ctx.clip()
        ctx.paint()

        ctx.set_source_rgb(bg_color.red, bg_color.green, bg_color.blue)
        self._draw_rounded_rectangle(ctx, 1, 1,
                                     extents.width + (offset * 2) - 2,
                                     extents.height + (offset * 2) - 2,
                                     2)
        ctx.fill()

        ctx.set_source_rgb(fg_color.red, fg_color.green, fg_color.blue)
        ctx.move_to(offset, offset + extents.height - 1)
        ctx.show_text(text)

    @staticmethod
    def _draw_rounded_rectangle(ctx, x, y, width, height, radius):
        degrees = PI / 180.0

        ctx.new_sub_path()
        ctx.arc(x + width - radius, y + radius, radius, -90 * degrees, 0 * degrees)
        ctx.arc(x + width - radius, y + height - radius, radius, 0 * degrees, 90 * degrees)
        ctx.arc(x + radius, y + height - radius, radius, 90 * degrees, 180 * degrees)
        ctx.arc(x + radius, y + radius, radius, 180 * degrees, 270 * degrees)
        ctx.close_path()

    def _on_focus_in(self, widget, cb_data):
        # self._show_hint_window()
        pass

    def _on_focus_out(self, widget, cb_data):
        # self._hint_window.set_visible(False)
        pass

    def _get_iter_at_event(self, event):
        _, x, y = event.get_coords()
        bx, by = self.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
        is_over_text, textiter = self.get_iter_at_location(bx, by)
        if is_over_text:
            return textiter

        return None

    def set_typewriter_mode(self, typewriter_mode, typewriter_mode_type=None):
        self._typewriter_mode = typewriter_mode
        if typewriter_mode:
            self._typewriter_mode_type = typewriter_mode_type
            area = GtkSource.View.get_visible_rect(self)
            if self.cached_char_height:
                visible_lines = int(area.height / self.cached_char_height)
                if self._typewriter_mode_type == TypewriterModeType.UPPER:
                    self.scroll_offset = (visible_lines - 1) / 4
                    self.overscroll_num_lines = (visible_lines - 1) / 4
                elif self._typewriter_mode_type == TypewriterModeType.LOWER:
                    self.scroll_offset = (visible_lines - 1) * 3 / 4
                    self.overscroll_num_lines = (visible_lines - 1) * 3 / 4
                else:
                    self.scroll_offset = (visible_lines - 1) / 2
                    self.overscroll_num_lines = self.scroll_offset
        else:
            self.scroll_offset = DEFAULT_SCROLL_OFFSET
            self.overscroll_num_lines = DEFAULT_NUM_OVERSCROLL

    def set_font(self, font_name, default_font=False):
        if default_font:
            settings = Gio.Settings('org.gnome.desktop.interface')
            font_name = settings.get_string('monospace-font-name')

        pango_font_desc = Pango.FontDescription.from_string(font_name)
        self.override_font(pango_font_desc)
