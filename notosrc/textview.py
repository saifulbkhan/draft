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

from gi.repository import Gtk, GObject, GtkSource, Gdk, GLib, Pango

from notosrc import file

# Ensure that GtkBuilder actually recognises SourceView in UI file
GObject.type_ensure(GObject.GType(GtkSource.View))


class TextView(Gtk.Box):
    def __repr__(self):
        return '<TextView>'

    def __init__(self, main_window, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/textview.ui')
        self.main_window = main_window
        self.parent = parent
        self._set_up_widgets()
        self.current_file = None
        self.current_file_etag = None

    def _set_up_widgets(self):
        self.scrollable = self.builder.get_object('scrollable')
        self.pack_start(self.scrollable, True, True, 0)
        self.status_bar = self.builder.get_object('status_bar')
        self.pack_start(self.status_bar, False, False, 0)
        self.view = NotoTextView()
        self.scrollable.add(self.view)

        self.view.set_pixels_above_lines(6)
        self.view.set_pixels_below_lines(6)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.view.set_left_margin(24)
        self.view.set_right_margin(24)
        self.view.set_top_margin(10)
        self.view.set_bottom_margin(10)
        self.view.scroll_offset = 4
        self.view.get_style_context().add_class('noto-editor')

        self.connect('key-press-event', self._on_key_press)

        buffer = self.view.get_buffer()
        self._on_buffer_changed_id = buffer.connect('changed',
                                                    self._on_buffer_changed)
        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language('markdown')
        buffer.set_language(language)

    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        # TODO: Add shortcuts to textview
        if event_and_modifiers:
            if (event.keyval == Gdk.KEY_s
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                pass

    def _on_buffer_changed(self, buffer):
        count = buffer.get_char_count()
        self.write_current_buffer()

    def load_file(self, res):
        self.current_file_etag = None
        if res:
            self.current_file, contents, self.current_file_etag = res
            self.render_content(contents)

        if self.parent.in_preview_mode():
            self.parent.preview_content()

    def render_content(self, contents):
        buffer = self.view.get_buffer()
        with buffer.handler_block((self._on_buffer_changed_id)):
            buffer.begin_not_undoable_action()
            buffer.set_text(contents)
            buffer.end_not_undoable_action()

        # TODO: Use mark to scroll to desired position, to avoid segfaults
        self.view.grab_focus()
        iter_at_cursor = buffer.get_iter_at_mark(buffer.get_insert())
        GLib.idle_add(self.view.scroll_to_iter,
                      iter_at_cursor,
                      0.0, True, 0.0, 0.5)

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


class NotoTextView(GtkSource.View):
    __gtype_name__ = 'NotoTextView'

    def __repr__(self):
        return '<NotoTextView>'

    def init(self):
        GtkSource.View.__init__(self)
        self.cached_char_height = 0
        self.cached_char_width = 0
        self.scroll_offset = 0

    def do_style_updated(self):
        GtkSource.View.do_style_updated(self)

        context = self.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text('X', 1)
        self.cached_char_width, self.cached_char_height = layout.get_pixel_size()
        self.cached_char_height += self.get_pixels_above_lines() +\
                                   self.get_pixels_below_lines()

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
        vadj.set_value(yvalue)

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

    def scroll_mark_onscreen(self, mark, use_align, xalign, yalign):
        visible_rect = self.get_visible_rect()
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        mark_rect = self.get_iter_location(text_iter)

        if not self._gdk_rectangle_contains(visible_rect, mark_rect):
            self.scroll_to_mark(mark, 0.0, use_align, xalign, yalign)

    def scroll_to_mark(self, mark, within_margin,
                       use_align, xalign, yalign):
        text_iter = self.get_buffer().get_iter_at_mark(mark)
        self.scroll_to_iter(text_iter, within_margin, use_align, xalign, yalign)
