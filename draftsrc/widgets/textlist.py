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

import cairo
from gettext import gettext as _

from gi.repository import Gtk, GLib, Pango, Gdk, GObject

from draftsrc.models.textliststore import DraftTextListStore, TextListType
from draftsrc.models.collectionliststore import CollectionClassType
from draftsrc.widgets import TEXT_MOVE_INFO, TEXT_MOVE_TARGET


class DraftTextList(Gtk.ListBox):
    """The listbox containing all the texts in a text group"""
    __gtype__name__ = 'DraftTextList'

    __gsignals__ = {
        'text-moved-to-group': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_PYOBJECT,)),
        'text-deleted': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'text-created': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    editor = None
    _texts_being_moved = []
    _multi_row_selection_stack = []

    def __repr__(self):
        return '<DraftTextList>'

    def __init__(self):
        """Initialize a new DraftTextsList for given @parent_group

        @parent_group: string, unique hash string for @parent_group
        """
        Gtk.ListBox.__init__(self)
        self.connect('key-press-event', self._on_key_press)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self._row_selected_handler_id = self.connect('row-selected',
                                                     self._on_row_selected)
        self.set_selection_mode(Gtk.SelectionMode.BROWSE)

    def _create_row_widget(self, text_data, user_data):
        """Create a row widget for @text_data"""
        data_dict = text_data.to_dict()
        title = data_dict['title']
        subtitle = data_dict['subtitle']

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_box.set_visible(True)
        row_box.set_spacing(2)
        for direction in ['left', 'right', 'top', 'bottom']:
            method = 'set_margin_%s' % direction
            getattr(row_box, method)(6)

        title_label = Gtk.Label()
        row_box.pack_start(title_label, True, False, 0)

        self._set_title_label(row_box, title)
        self._append_subtitle_label(row_box, subtitle)

        event_box = Gtk.EventBox()
        event_box.add(row_box)
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                  [TEXT_MOVE_TARGET],
                                  Gdk.DragAction.MOVE)
        event_box.connect('drag-data-get', self._drag_data_get)
        event_box.connect('drag-begin', self._drag_begin)
        return event_box

    def _set_title_label(self, box, title):
        """Set label for @label to @title"""
        labels = box.get_children()
        label = labels[0]
        label.set_markup('<b>%s</b>' % title)
        self._shape_row_label(label)

    def _append_subtitle_label(self, box, subtitle):
        """Set label for @label to @subtitle"""
        subtitle_label = None
        labels = box.get_children()

        # check if subtitle label already exists
        if len(labels) > 1:
            subtitle_label = labels[1]
        else:
            subtitle_label = Gtk.Label()
            box.pack_start(subtitle_label, True, False, 1)

        if subtitle is None:
            box.remove(subtitle_label)
            return

        subtitle_label.set_label(subtitle)
        subtitle_label.set_line_wrap(True)
        subtitle_label.set_lines(3)
        subtitle_label.set_xalign(0.0)
        self._shape_row_label(subtitle_label)

    def _shape_row_label(self, label):
        """Perform some general adjustments on label for row widgets"""
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_halign(Gtk.Align.START)
        label.set_visible(True)

    def _on_key_press(self, widget, event):
        """Handler for signal `key-press-event`"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            # Delete row and file with (Del)
            if event.keyval == Gdk.KEY_Delete:
                self.delete_selected_row()

    def _row_at_event_coordinates(self, event):
        device = event.device
        win = device.get_window_at_position()[0]
        x, y, width, height = win.get_geometry()
        return self.get_row_at_y(y)

    def _on_button_press(self, widget, event):
        """Handler for signal `button-press-event`"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)


        if modifiers:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK

            if (event.button == Gdk.BUTTON_PRIMARY
                    and modifiers == control_mask):
                self.set_multi_selection_mode(True)
                row = self._row_at_event_coordinates(event)
                if row.is_selected() and len(self.get_selected_rows()) > 1:
                    self.unselect_row(row)
                    row.set_selectable(False)
                    if row in self._multi_row_selection_stack:
                        self._multi_row_selection_stack.remove(row)
                else:
                    row.set_selectable(True)
            elif (event.button == Gdk.BUTTON_PRIMARY
                    and modifiers == shift_mask):
                self.set_multi_selection_mode(True)
                row = self._row_at_event_coordinates(event)
                row_end = row.get_index()
                row.set_selectable(True)

                if not self._multi_row_selection_stack:
                    selected_row = self.get_selected_row()
                    self._multi_row_selection_stack.append(selected_row)

                row = self._multi_row_selection_stack[-1]
                row_start = row.get_index()
                if row_start > row_end:
                    row_end = row_start + row_end
                    row_start = row_end - row_start
                    row_end = row_end - row_start
                for i in range(row_start, row_end):
                    row = self.get_row_at_index(i)
                    row.set_selectable(True)
                    self.select_row(row)

    def _on_button_release(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if not modifiers:
            if event.button == Gdk.BUTTON_PRIMARY:
                row = self._row_at_event_coordinates(event)
                row.set_selectable(True)
                self.set_multi_selection_mode(False)

    def _on_row_selected(self, widget, row):
        """Handler for signal `row-selected`"""
        if not row:
            return

        if self.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self._multi_row_selection_stack.append(row)
            return

        position = row.get_index()
        row_data = self._model.get_data_for_position(position)
        if row_data['in_trash']:
            self.editor.set_sensitive(False)
        else:
            self.editor.set_sensitive(True)

        self._model.prepare_for_edit(position,
                                    self.editor.switch_view,
                                    self.editor.load_file)

    def _on_items_changed(self, model, position, removed, added):
        """Handler for model's `items-changed` signal"""
        row = self.get_row_at_index(position)
        GLib.idle_add(self.select_row, row)

    def _drag_begin(self, widget, drag_context):
        """When drag action begins this function does several things:
        1. find the row for @widget,
        2. estimate the number of rows being moved
        3. unselect it (if selected)
        4. add a frame style for opaque background and borders
        5. create a cairo surface for row (if single), a text surface otherwise
        6. set it as icon for the drag context
        7. remove the frame style
        8. set the row as selected"""
        row = widget.get_ancestor(Gtk.ListBoxRow.__gtype__)
        num_selected = len(self.get_selected_rows())
        if (not row.is_selected()
                and self.get_selection_mode() == Gtk.SelectionMode.MULTIPLE):
            num_selected += 1

        self.unselect_row(row)
        style_context = row.get_style_context()
        style_context.add_class('draft-drag-icon')
        allocation = row.get_allocation()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     allocation.width,
                                     allocation.height)

        context = cairo.Context(surface)
        if num_selected > 1:
            style_ctx = self.get_style_context()
            font = style_ctx.get_font(style_ctx.get_state())
            border_success, border_color = style_ctx.lookup_color('borders')
            bg_success, bg_color = style_ctx.lookup_color('content_view_bg')
            fg_success, fg_color = style_ctx.lookup_color('theme_fg_color')
            if border_success and bg_success and fg_success:
                offset = 10
                font_size = int((font.get_size() / Pango.SCALE) * 96 / 72)
                context.set_font_size(font_size)
                font_family = font.get_family()
                context.select_font_face(font_family,
                                         cairo.FontSlant.NORMAL,
                                         cairo.FontWeight.BOLD)
                text = _(" items selected")
                text = str(num_selected) + text
                extents = context.text_extents(text)
                context.set_source_rgba(border_color.red,
                                        border_color.green,
                                        border_color.blue)
                context.rectangle(0, 0,
                                  extents.width + (offset * 2),
                                  extents.height + (offset * 2))
                context.fill()
                context.set_source_rgb(bg_color.red,
                                       bg_color.green,
                                       bg_color.blue)
                context.rectangle(1, 1,
                                  (extents.width + (offset * 2)) - 2,
                                  (extents.height + (offset * 2)) - 2)
                context.fill()
                context.set_source_rgba(fg_color.red,
                                        fg_color.green,
                                        fg_color.blue)
                context.move_to(offset, offset + extents.height)
                context.show_text(text)
        else:
            row.draw(context)

        Gtk.drag_set_icon_surface(drag_context, surface)
        style_context.remove_class('draft-drag-icon')
        self.select_row(row)

    def _drag_data_get(self, widget, drag_context, selection, info, time):
        """Supply selection data with the db id of the row being dragged"""
        rows = self.get_selected_rows()
        positions = [row.get_index() for row in rows]
        text_data_list = [self._model.get_data_for_position(position)
                          for position in positions]
        ids = [text_data['id'] for text_data in text_data_list]

        selection.set(selection.get_target(), -1, bytearray(ids))
        self._texts_being_moved = ids

    def set_model(self, collection_class=None, parent_group=None, tag=None):
        self._model = None
        if parent_group:
            if parent_group['in_trash']:
                self._model = DraftTextListStore(list_type=TextListType.GROUP_TEXTS,
                                                 parent_group=parent_group,
                                                 trashed=True)
            else:
                self._model = DraftTextListStore(list_type=TextListType.GROUP_TEXTS,
                                                 parent_group=parent_group)
        elif tag:
            self._model = DraftTextListStore(list_type=TextListType.TAGGED_TEXTS,
                                             tag=tag)
        else:
            if collection_class == CollectionClassType.RECENT:
                self._model = DraftTextListStore(list_type=TextListType.RECENT_TEXTS)
            else:
                self._model = DraftTextListStore(list_type=TextListType.ALL_TEXTS)

        self.bind_model(self._model, self._create_row_widget, None)
        self._model.connect('items-changed', self._on_items_changed)
        if self._texts_being_moved:
            if len(self._texts_being_moved) > 1:
                self.set_multi_selection_mode(True)
            positions = [self._model.get_position_for_id(text_id)
                         for text_id in self._texts_being_moved]
            if positions:
                for position in positions:
                    row = self.get_row_at_index(position)
                    self.select_row(row)
            self._texts_being_moved = []
        else:
            position = self._model.get_latest_modified_position()
            if position is not None:
                row = self.get_row_at_index(position)
                self.select_row(row)

    def set_editor(self, editor):
        """Set editor for @self

        @self: DraftTextsList
        @editor: DraftEditor, the editor to display selected texts and listen
                 for changes that need to be conveyed to the backend
        """
        self.editor = editor
        editor.connect('title-changed', self.set_title_for_current_selection)
        editor.connect('subtitle-changed', self.set_subtitle_for_current_selection)
        editor.connect('markup-changed', self.set_markup_for_current_selection)
        editor.connect('word-goal-set', self.set_word_goal_for_current_selection)
        editor.connect('tags-changed', self.set_tags_for_current_selection)
        editor.connect('view-changed', self.save_last_edit_data)

    def set_multi_selection_mode(self, multi_mode, escape=False):
        """Set or unset multiple selection mode for the ListView"""
        if multi_mode:
            if hasattr(self, 'editor'):
                self.editor.set_sensitive(False)
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        else:
            if hasattr(self, 'editor'):
                self.editor.set_sensitive(True)
            self.set_selection_mode(Gtk.SelectionMode.BROWSE)
            self._multi_row_selection_stack.clear()

            if escape:
                position = self._model.get_latest_modified_position()
                if position is not None:
                    row = self.get_row_at_index(position)
                    self.select_row(row)

    def new_text_request(self):
        """Request for creation of a new text and append it to the list"""
        self._model.new_text_request()
        self.emit('text-created')

    def set_group_for_ids(self, text_ids, group):
        """Send texts with @text_ids to the group with id @group. Assuming this
        is not the same group as the texts is currently in, it will be removed
        from the selected model."""
        for text_id in text_ids:
            pos = self._model.get_position_for_id(text_id)
            if pos is not None:
                text_id = self._model.set_prop_for_position(pos,
                                                            'parent_id',
                                                            group)
        self.emit('text-moved-to-group', group)

    def set_title_for_current_selection(self, widget, title):
        """Set the title for currently selected text, as well as write this to
        the db.

        @self: DraftTextsList
        @title: string, the title to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'title', title)
        self.editor.current_text_data['title'] = title

        box = row.get_child().get_child()
        self._set_title_label(box, title)

    def set_subtitle_for_current_selection(self, widget, subtitle):
        """Set the subtitle for currently selected text, as well as write this
        to the db.

        @self: DraftTextsList
        @subtitle: string, the subtitle to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'subtitle', subtitle)
        self.editor.current_text_data['subtitle'] = subtitle

        box = row.get_child().get_child()
        self._append_subtitle_label(box, subtitle)

    def set_markup_for_current_selection(self, widget, markup):
        """Save the markup for currently selected text to the db.

        @self: DraftTextsList
        @markup: string, the markup to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'markup', markup)
        self.editor.current_text_data['markup'] = markup

    def set_word_goal_for_current_selection(self, widget, goal):
        """Save the word count goal for currently selected text to the db.

        @self: DraftTextsList
        @markup: int, the word count goal to be saved for current selection
        """
        row = self.get_selected_row()
        position = row.get_index()
        self._model.set_prop_for_position(position, 'word_goal', goal)
        self.editor.current_text_data['word_goal'] = goal

    def set_tags_for_current_selection(self, widget, tags):
        """Ask store to make changes to the tags of the currently selected text
        so that it can be written to db.

        @self: DraftTextsList
        @tags: list, the list of string tags which the selected text will be
               tagged with.
        """
        row = self.get_selected_row()
        position = row.get_index()
        new_tags = self._model.set_tags_for_position(position, tags)

        # since @new_tags might have slightly different letter case tags, we
        # should re-update editor tags as well and then update statusbar, though
        # this is probably not the best place to do it.
        self.editor.current_text_data['tags'] = new_tags
        self.editor.statusbar.update_text_data()

    def save_last_edit_data(self, widget, metadata):
        """Save last metdata that would be associated with the last edit session
        of the text.

        @self: DraftTextsList
        @metadata: dict, contains metadata associated with a text
        """
        if metadata:
            self._model.queue_final_save(metadata)

    def delete_selected_row(self):
        """Delete currently selected text in the list"""
        position = self.get_selected_row().get_index()
        self._model.delete_item_at_postion(position)
        self.emit('text-deleted')
