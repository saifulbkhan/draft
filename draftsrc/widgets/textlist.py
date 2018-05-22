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


class DraftBaseList(Gtk.ListBox):
    """A list view widget meant for displaying texts"""
    __gtype_name__ = 'DraftBaseList'

    __gsignals__ = {
        'text-title-changed': (GObject.SignalFlags.RUN_FIRST,
                               None,
                               (GObject.TYPE_STRING,
                                GObject.TYPE_STRING,
                                GObject.TYPE_BOOLEAN)),
        'menu-requested': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           (GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN)),
        'some-text-selected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'no-text-selected': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    editor = None
    _double_click_in_progress = False
    _text_view_selection_in_progress = False
    _items_changed_handler_id =None

    def __repr__(self):
        return '<DraftBaseList>'

    def __init__(self):
        Gtk.ListBox.__init__(self)
        self.connect('button-press-event', self._on_button_press_base)
        self.connect('button-release-event', self._on_button_release_base)
        self._row_selected_handler_id = self.connect('row-selected',
                                                     self._on_row_selected)
        self.connect('row-activated', self._on_row_activated)
        self.set_activate_on_single_click(False)
        self.set_selection_mode(Gtk.SelectionMode.BROWSE)

    def _row_at_event_coordinates(self, event):
        device = event.device
        win = device.get_window_at_position()[0]
        x, y, width, height = win.get_geometry()
        return self.get_row_at_y(y)

    def _on_button_press_base(self, widget, event):
        """Handler for signal `button-press-event`"""
        if not hasattr(self, '_model'):
            return

        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if modifiers:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK

            if (event.button == Gdk.BUTTON_PRIMARY
                    and (modifiers == control_mask or modifiers == shift_mask)):
                self.set_multi_selection_mode(True)
        else:
            if event.triggers_context_menu():
                row = self._row_at_event_coordinates(event)
                if not row:
                    return
                self.select_row(row)
                rect = row.get_allocation()
                position = row.get_index()
                row_data = self._model.get_data_for_position(position)
                self.emit('menu-requested', rect, row_data['in_trash'])
            elif (event.button == Gdk.BUTTON_PRIMARY
                    and event.type == Gdk.EventType._2BUTTON_PRESS):
                self._double_click_in_progress = True

    def _on_button_release_base(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if not modifiers:
            if event.button == Gdk.BUTTON_PRIMARY:
                if self._double_click_in_progress:
                    GLib.idle_add(self.editor.focus_view, True)
                    self._double_click_in_progress = False

                row = self._row_at_event_coordinates(event)
                if not row:
                    return
                self.set_multi_selection_mode(False)

    def _on_row_selected(self, widget, row):
        """Handler for signal `row-selected`"""
        if (not hasattr(self, '_model')
                or self._text_view_selection_in_progress):
            return

        if not row and not self.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            return

        def on_row_unfocused(widget, cb_data=None):
            if not self.get_focus_child():
                self._set_listview_class(True)

        def on_row_focused(widget, cb_data=None):
            self._set_listview_class(False)

        # if row loses focus then grayed selection, but if selection is within
        # the list itself then remove gray selection class
        if row:
            row.grab_focus()
            row.connect('focus-out-event', on_row_unfocused)
            row.connect('focus-in-event', on_row_focused)
            self._set_listview_class(False)

        positions = []
        for row in self.get_selected_rows():
            position = row.get_index()
            positions.append(position)
            if self._model.trashed_texts_only:
                self.editor.set_sensitive(False)
            else:
                self.editor.set_sensitive(True)

        if len(positions) > 0:
            self.emit('some-text-selected')
        else:
            self.emit('no-text-selected')

        self._model.prepare_for_edit(positions,
                                     self.editor.switch_view,
                                     self.editor.load_file)

    def _on_row_activated(self, widget, row):
        GLib.idle_add(self.editor.focus_view, True)

    def _set_listview_class(self, set_class):
        listview_class = 'draft-listview'
        ctx = self.get_style_context()
        if set_class and not ctx.has_class(listview_class):
            ctx.add_class(listview_class)
        elif not set_class and ctx.has_class(listview_class):
            ctx.remove_class(listview_class)

    def set_multi_selection_mode(self, multi_mode, escape=False):
        """Set or unset multiple selection mode for the ListView"""
        if not hasattr(self, '_model'):
            return

        if multi_mode:
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        else:
            self.set_selection_mode(Gtk.SelectionMode.BROWSE)

            if escape:
                position = self._model.get_latest_modified_position()
                if position is not None:
                    row = self.get_row_at_index(position)
                    self.select_row(row)

    def set_editor(self, editor):
        """Set editor for @self

        @self: DraftBaseList
        @editor: DraftEditor, the editor to display selected texts and listen
                 for changes that need to be conveyed to the backend
        """
        self.editor = editor
        editor.connect('title-changed', self.set_title_for_selection)
        editor.connect('subtitle-changed', self.set_subtitle_for_selection)
        editor.connect('markup-changed', self.set_markup_for_selection)
        editor.connect('word-goal-set', self.set_word_goal_for_selection)
        editor.connect('tags-changed', self.set_tags_for_selection)
        editor.connect('view-modified', self.save_last_edit_data)
        editor.connect('view-changed', self.set_header_title_for_view)

    def set_title_for_selection(self, widget, title):
        """Set the title for currently selected text, as well as write this to
        the db.

        @self: DraftTextsList
        @title: string, the title to be saved for current selection
        """
        if not hasattr(self, '_model'):
            return

        text_id = self.editor.current_text_data['id']
        position = self.get_selected_index_for_id(text_id)
        self._model.set_prop_for_position(position, 'title', title)
        self.editor.current_text_data['title'] = title

    def set_subtitle_for_selection(self, widget, subtitle):
        """Set the subtitle for currently selected text, as well as write this
        to the db.

        @self: DraftTextsList
        @subtitle: string, the subtitle to be saved for current selection
        """
        if not hasattr(self, '_model'):
            return

        text_id = self.editor.current_text_data['id']
        position = self.get_selected_index_for_id(text_id)
        self._model.set_prop_for_position(position, 'subtitle', subtitle)
        self.editor.current_text_data['subtitle'] = subtitle

    def set_markup_for_selection(self, widget, markup):
        """Save the markup for currently selected text to the db.

        @self: DraftTextsList
        @markup: string, the markup to be saved for current selection
        """
        if not hasattr(self, '_model'):
            return

        text_id = self.editor.current_text_data['id']
        position = self.get_selected_index_for_id(text_id)
        self._model.set_prop_for_position(position, 'markup', markup)
        self.editor.current_text_data['markup'] = markup

    def set_word_goal_for_selection(self, widget, goal):
        """Save the word count goal for currently selected text to the db.

        @self: DraftTextsList
        @markup: int, the word count goal to be saved for current selection
        """
        if not hasattr(self, '_model'):
            return

        text_id = self.editor.current_text_data['id']
        position = self.get_selected_index_for_id(text_id)
        self._model.set_prop_for_position(position, 'word_goal', goal)
        self.editor.current_text_data['word_goal'] = goal

    def set_tags_for_selection(self, widget, tags):
        """Ask store to make changes to the tags of the currently selected text
        so that it can be written to db.

        @self: DraftTextsList
        @tags: list, the list of string tags which the selected text will be
               tagged with.
        """
        if not hasattr(self, '_model'):
            return

        text_id = self.editor.current_text_data['id']
        position = self.get_selected_index_for_id(text_id)
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
        if not hasattr(self, '_model'):
            return

        if metadata:
            self._model.queue_final_save(metadata)

    def set_header_title_for_view(self, widget, title, position, total):
        """Sets the headerbar title for the item being viewed. Also set the
        subtitle, if multiple items selected. """
        subtitle = ""
        if position and total:
            subtitle = _("%s of %s") % (position, total)
        self.emit('text-title-changed', title, subtitle, True)

    def activate_selected_row(self):
        """Activate selected row"""
        row = self.get_selected_row()
        row.emit('activate')

    def select_for_id(self, text_id):
        if not hasattr(self, '_model'):
            return

        position = self._model.get_position_for_id(text_id)
        if position is not None:
            row = self.get_row_at_index(position)
            if row and not row.is_selected():
                self.select_row(row)

    def finish_selection_for_id(self, text_id):
        self.select_for_id(text_id)
        self._text_view_selection_in_progress = False

    def text_view_selection_is_in_progress(self):
        return self._text_view_selection_in_progress

    def get_num_items(self):
        if self._model is not None:
            return self._model.get_n_items()
        return 0

    def get_selected_index_for_id(self, text_id):
        positions = []
        rows = self.get_selected_rows()
        for row in rows:
            pos = row.get_index()
            positions.append(pos)

        return self._model.get_position_for_id_in_range(text_id, positions)


class DraftTextList(DraftBaseList):
    """The listbox containing all the texts in a text group"""
    __gtype__name__ = 'DraftTextList'

    __gsignals__ = {
        'text-moved-to-group': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_PYOBJECT,)),
        'text-deleted': (GObject.SignalFlags.RUN_FIRST,
                         None, (GObject.TYPE_BOOLEAN,)),
        'text-restored': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'text-created': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'selection-requested': (GObject.SignalFlags.RUN_FIRST,
                                None,
                                (GObject.TYPE_PYOBJECT,
                                 GObject.TYPE_PYOBJECT,
                                 GObject.TYPE_BOOLEAN))
    }

    _texts_being_moved = []

    def __repr__(self):
        return '<DraftTextList>'

    def __init__(self):
        """Initialize a new DraftTextsList, without any items. Use `set_model`
        for setting a model and populating view with items."""
        DraftBaseList.__init__(self)
        self.connect('key-press-event', self._on_key_press)

    def _create_row_widget(self, text_data, user_data):
        """Create a row widget for @text_data"""
        data_dict = text_data.to_dict()
        title = data_dict['title']
        subtitle = data_dict['subtitle']

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_box.set_visible(True)
        ctx = row_box.get_style_context()
        ctx.add_class('draft-text-box-row')

        title_label = Gtk.Label()
        row_box.pack_start(title_label, True, False, 0)

        self._set_title_label(row_box, title)
        self._append_subtitle_label(row_box, subtitle)

        event_box = Gtk.EventBox()
        event_box.add(row_box)
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                  [TEXT_MOVE_TARGET],
                                  Gdk.DragAction.MOVE)
        event_box.connect('drag-data-get', self._on_drag_data_get)
        event_box.connect('drag-begin', self._on_drag_begin)
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
        subtitle_label.set_margin_top(6)
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
                self.delete_selected()

    def _on_items_changed(self, model, position, removed, added):
        """Handler for model's `items-changed` signal"""
        position_to_select = position
        num_items = self._model.get_n_items()
        if position_to_select >= num_items:
            position_to_select = num_items - 1
        if position_to_select < 0:
            position_to_select = 0
        row = self.get_row_at_index(position_to_select)
        if row:
            GLib.idle_add(self.select_row, row)

    def _on_drag_begin(self, widget, drag_context):
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

    def _on_drag_data_get(self, widget, drag_context, selection, info, time):
        """Supply selection data with the db id of the row being dragged"""
        rows = self.get_selected_rows()
        positions = [row.get_index() for row in rows]
        text_data_list = [self._model.get_data_for_position(position)
                          for position in positions]
        ids = [text_data['id'] for text_data in text_data_list]

        selection.set(selection.get_target(), -1, bytearray(ids))
        self._texts_being_moved = ids

    def _on_text_viewed(self, widget, text_metadata):
        """Select the text in textlist for which given metadata has been
        provided"""
        if not hasattr(self, '_model'):
            return

        list_type, group, in_trash = self._model.get_model_attributes()
        if list_type == TextListType.GROUP_TEXTS:
            group_id = text_metadata['parent_id']
            text_id = text_metadata['id']
            self._text_view_selection_in_progress = True
            if group['id'] != text_metadata['parent_id']:
                if in_trash and group_id is not None:
                    pos = self._model.get_position_for_id(text_id)
                    if pos is not None:
                        _, parent_group = self._model.get_data_for_position(pos,
                                                                            True)
                        if not parent_group['in_trash']:
                            group_id = None
                self.emit('selection-requested', group_id, text_id, in_trash)
            else:
                self.finish_selection_for_id(text_id)

    def set_editor(self, editor):
        """Set editor and connect any other signal(s)."""
        DraftBaseList.set_editor(self, editor)
        editor.connect('text-viewed', self._on_text_viewed)

    def set_model(self, collection_class=None, parent_group=None):
        self._model = None
        if parent_group:
            if parent_group['in_trash']:
                self._model = DraftTextListStore(list_type=TextListType.GROUP_TEXTS,
                                                 parent_group=parent_group,
                                                 trashed=True)
            else:
                self._model = DraftTextListStore(list_type=TextListType.GROUP_TEXTS,
                                                 parent_group=parent_group)
        else:
            if collection_class == CollectionClassType.RECENT:
                self._model = DraftTextListStore(list_type=TextListType.RECENT_TEXTS)
            else:
                self._model = DraftTextListStore(list_type=TextListType.ALL_TEXTS)

        with self.handler_block(self._row_selected_handler_id):
            self.bind_model(self._model, self._create_row_widget, None)
        self._items_changed_handler_id = self._model.connect('items-changed',
                                                             self._on_items_changed)
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
        self._set_listview_class(True)

    def new_text_request(self):
        """Request for creation of a new text and append it to the list"""
        self._model.new_text_request()
        position = self._model.get_latest_modified_position()
        self.select_row(self.get_row_at_index(position))
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

    def set_title_for_selection(self, widget, title):
        DraftBaseList.set_title_for_selection(self, widget, title)
        row = self.get_selected_row()
        box = row.get_child().get_child()
        self._set_title_label(box, title)
        self.emit('text-title-changed', title, "", False)

    def set_subtitle_for_selection(self, widget, subtitle):
        DraftBaseList.set_subtitle_for_selection(self, widget, subtitle)
        row = self.get_selected_row()
        box = row.get_child().get_child()
        self._append_subtitle_label(box, subtitle)

    def delete_selected(self, permanent=False):
        """Delete currently selected texts in the list"""
        selected_rows = self.get_selected_rows()
        self.delete_rows(selected_rows, permanent=permanent)
        self.set_multi_selection_mode(False)
        self.emit('text-deleted', permanent)

    def restore_selected(self):
        """Restore the currently selected rows, which is expected to be already
        in trash"""
        selected_rows = self.get_selected_rows()
        for row in selected_rows:
            position = row.get_index()
            self._model.restore_item_at_position(position)

        self.set_multi_selection_mode(False)
        self.emit('text-restored')

    def selected_rows_will_be_orphaned(self):
        """Check if the currently selected row in list will be orphaned if we
        restore the text from trash"""
        count = 0
        selected_rows = self.get_selected_rows()
        for row in selected_rows:
            position = row.get_index()
            text, parent_group = self._model.get_data_for_position(position,
                                                                   parent_group=True)
            if parent_group and parent_group['in_trash']:
                count += 1
        return count

    def delete_rows(self, rows, permanent=False):
        for row in rows:
            position = row.get_index()
            if permanent:
                self._model.delete_item_at_postion_permanently(position)
            else:
                self._model.delete_item_at_postion(position)

    def delete_all_rows_permanently(self):
        all_rows = self.get_children()
        with self.handler_block(self._row_selected_handler_id):
            with self._model.handler_block(self._items_changed_handler_id):
                self.delete_rows(all_rows, permanent=True)
        self.emit('text-deleted', True)


class DraftResultList(DraftBaseList):
    """The listbox containing results of a text search"""
    __gtype__name__ = 'DraftTextList'

    _showing_tagged_results = False

    def __repr__(self):
        return '<DraftResultList>'

    def __init__(self):
        DraftBaseList.__init__(self)

    def _create_row_widget(self, text_data, user_data):
        """Create a row widget for @text_data"""
        data_dict = text_data.to_dict()
        title = data_dict['title']
        highlights = data_dict['misc']

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_box.set_visible(True)
        ctx = row_box.get_style_context()
        ctx.add_class('draft-text-box-row')

        title_label = Gtk.Label()
        row_box.pack_start(title_label, True, False, 0)

        if self._showing_tagged_results:
            tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row_box.pack_start(tags_box, True, False, 0)
        else:
            highlights_label = Gtk.Label()
            row_box.pack_start(highlights_label, True, False, 0)

        self._set_title_label(row_box, title)
        self._append_highlights(row_box, highlights)

        return row_box

    def _set_title_label(self, box, title):
        """Set label for @label to @title"""
        labels = box.get_children()
        label = labels[0]
        label.set_markup('<b>%s</b>' % title)
        self._shape_row_label(label)

    def _append_highlights(self, box, highlights):
        """Append highlights to the row"""
        if self._showing_tagged_results:
            children = box.get_children()
            tags_box = children[1]
            tags_box.set_margin_top(6)
            for match in highlights:
                tag_label = match[1].decode('utf-8')
                label = Gtk.Label(tag_label)
                label.get_style_context().add_class('draft-tag-label')
                tags_box.add(label)
            tags_box.show_all()
        else:
            labels = box.get_children()
            label = labels[1]
            label.set_markup(highlights)
            label.set_margin_top(6)
            self._shape_row_label(label)

    def _shape_row_label(self, label):
        """Perform some general adjustments on label for row widgets"""
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_halign(Gtk.Align.START)
        label.set_visible(True)

    def _on_items_changed(self, model, position, removed, added):
        """Handler for model's `items-changed` signal"""
        position_to_select = position
        num_items = self._model.get_n_items()
        if position_to_select >= num_items:
            position_to_select = num_items - 1
        if position_to_select < 0:
            position_to_select = 0
        row = self.get_row_at_index(position_to_select)
        if row:
            GLib.idle_add(self.select_row, row)

    def set_model(self, results=None, tagged_results=False, trashed=False):
        self._model = DraftTextListStore(list_type=TextListType.RESULT_TEXTS,
                                         results=results,
                                         trashed=trashed)
        self._showing_tagged_results = tagged_results
        self.bind_model(self._model, self._create_row_widget, None)
        self._items_changed_handler_id = self._model.connect('items-changed',
                                                             self._on_items_changed)

    def set_editor(self, editor):
        self.editor = editor
