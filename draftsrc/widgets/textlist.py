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
from xml.sax.saxutils import escape as xml_escape

from gi.repository import Gtk, GLib, Pango, Gdk, GObject

from draftsrc.widgetmodels.textliststore import DraftTextListStore, TextListType
from draftsrc.widgetmodels.collectionliststore import CollectionClassType
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
        'no-text-selected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'reveal-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _editor = None
    _double_click_in_progress = False
    _text_view_selection_in_progress = False
    _items_changed_handler_id =None

    def __repr__(self):
        return '<DraftBaseList>'

    def __init__(self):
        Gtk.ListBox.__init__(self)
        self.connect('button-press-event', self._on_button_press_base)
        self.connect('button-release-event', self._on_button_release_base)
        self._row_selected_handler = self.connect('row-selected',
                                                  self._on_row_selected)
        self._rows_changed_handler = self.connect('selected-rows-changed',
                                                  self._on_selected_rows_changed)
        self.connect('row-activated', self._on_row_activated)
        self.set_activate_on_single_click(False)
        self.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.set_can_focus(True)

    def _row_at_event_coordinates(self, event):
        """Given a Gdk.ButtonEvent, obtains the row the pointer was pointing
        to when the event occurred

        :param event: a Gdk.ButtonEvent type of event

        :returns: the index of row at pointer if found
        :rtype: a non-negative int or None
        """
        device = event.device
        win = device.get_window_at_position()[0]
        x, y, width, height = win.get_geometry()
        return self.get_row_at_y(y)

    def _on_button_press_base(self, widget, event):
        """Handler for signal ``button-press-event`` signal"""
        if not hasattr(self, '_model'):
            return

        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if modifiers:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK

            if (event.button == Gdk.BUTTON_PRIMARY and
                    (modifiers == control_mask or modifiers == shift_mask)):
                self.set_multi_selection_mode(True)
        else:
            if event.triggers_context_menu():
                row = self._row_at_event_coordinates(event)
                if not row:
                    return
                self.select_row(row)
                rect = row.get_allocation()
                position = row.get_index()
                row_data = self._model.get_item(position)
                self.emit('menu-requested', rect, row_data.in_trash)
            elif (event.button == Gdk.BUTTON_PRIMARY and
                    event.type == Gdk.EventType._2BUTTON_PRESS):
                self._double_click_in_progress = True

    def _on_button_release_base(self, widget, event):
        """Handler for signal ``button-release-event`` signal"""
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
                elif self.in_multi_selection_mode():
                    self.set_multi_selection_mode(False)
                    self.select_row(row)

    def _on_row_selected(self, widget, row):
        """Handler for signal ``row-selected`` signal"""
        if (not hasattr(self, '_model') or
                self.text_view_selection_in_progress):
            return

        if not row and not self.in_multi_selection_mode():
            if len(self.get_selected_rows()) == 0:
                self.emit('no-text-selected')
            return

        # if row loses focus then grayed selection, but if selection is within
        # the list itself then remove gray selection class
        if row:
            row.grab_focus()
            self._set_focused_listview_class(False)

        positions = [row.get_index() for row in self.get_selected_rows()]
        if len(positions) > 0:
            self.emit('some-text-selected')
        else:
            self.emit('no-text-selected')

        self._model.prepare_for_edit(positions,
                                     self.editor.switch_view,
                                     self.editor.load_file)

    def _on_selected_rows_changed(self, widget):
        """Handler for signal ``selected-rows-changed`` signal"""
        self._on_row_selected(widget, None)

    def _on_row_activated(self, widget, row):
        """Handler for signal ``row-activated`` signal"""
        GLib.idle_add(self.editor.focus_view, True)

    def items_changed_base(self, model, position, removed, added):
        """Handler for model's ``items-changed`` signal"""
        if removed or added:
            position_to_select = position
            num_items = self._model.get_n_items()
            if position_to_select >= num_items:
                position_to_select = num_items - 1
            if position_to_select < 0:
                position_to_select = 0
            row = self.get_row_at_index(position_to_select)
            if row:
                GLib.idle_add(self.select_row, row)

    def _set_focused_listview_class(self, set_class):
        """Sets or unsets a style class on ``self`` that highlights selected
        rows with a theme-specific color.

        :param set_class: Add or remove class from widget's style context
        """
        listview_class = 'draft-focused-listview'
        ctx = self.get_style_context()
        if set_class and not ctx.has_class(listview_class):
            ctx.add_class(listview_class)
        elif not set_class and ctx.has_class(listview_class):
            ctx.remove_class(listview_class)

    def set_multi_selection_mode(self, multi_mode):
        """A simple wrapper to increase the verbosity of setting
        multi-selection mode

        :param multi_mode: Set or unset multi-selection mode"""
        if multi_mode:
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        else:
            self.set_selection_mode(Gtk.SelectionMode.BROWSE)

    def in_multi_selection_mode(self):
        """Check ``self`` for multi-selection mode

        :returns: If multi-selection mode is active or not
        :rtype: bool
        """
        return self.get_selection_mode() == Gtk.SelectionMode.MULTIPLE

    @GObject.Property(type=GObject.TYPE_PYOBJECT)
    def editor(self):
        """Getter for ``editor`` property. This editor displays selected texts
        and signals editing changes that need to be conveyed to the backend

        :returns: The editor associated with ``self``
        :rtype: DraftEditor
        """
        return self._editor

    @editor.setter
    def editor(self, editor):
        """Setter for ``editor`` prop

        :param editor: a DraftEditor
        """
        self._editor = editor
        editor.connect('view-transposed', self._on_view_transposed)
        editor.connect('escape-edit', self._on_escape_edit)

    def _on_view_transposed(self, widget, title, position, total):
        """Sets the headerbar title for the item being viewed. Also set the
        subtitle, if multiple items selected

        :param title: A title string for the headerbar
        :param position: The position of the visible text within selected views
        """
        subtitle = ""
        if position and total:
            subtitle = _("{} of {}".format(position, total))
        self.emit('text-title-changed', title, subtitle, True)

    def _on_escape_edit(self, widget):
        """Reveal the current visible text, select and focus it within the
        ListBox"""
        self.emit('reveal-requested')
        self.selected_row_grab_focus()

    def selected_row_grab_focus(self):
        """Focus the currently selected row in the ListBox"""
        row = self.get_selected_row()
        if row is not None:
            row.grab_focus()

    def activate_selected_row(self):
        """Manually activate selected row"""
        row = self.get_selected_row()
        row.emit('activate')

    def select_for_id(self, text_id):
        """Select the text, if present, with the given db id

        :param text_id: valid integer id of a text
        """
        if not hasattr(self, '_model'):
            return

        position = self._model.get_position_for_id(text_id)
        if position is not None:
            row = self.get_row_at_index(position)
            if row and not row.is_selected():
                self.select_row(row)

        self.text_view_selection_in_progress = False

    @GObject.Property(type=bool, default=False)
    def text_view_selection_in_progress(self):
        """Helps to check if there are any current selections in progress, i.e.
        if there are any outstanding selection requests within the ListBox

        :returns: Whether selections are in progress or not
        :rtype: bool
        """
        return self._text_view_selection_in_progress

    @text_view_selection_in_progress.setter
    def text_view_selection_in_progress(self, value):
        self._text_view_selection_in_progress = value

    def get_num_items(self):
        """Get the number of items within the ListBox

        :returns: number of items in ListBox
        :rtype: int"""
        if self._model is not None:
            return self._model.get_n_items()
        return 0

    def get_selected_index_for_id(self, text_id):
        """Within the selected rows, get the position of the row representing
        text with ``text_id``.

        :param text_id: valid db id of a text

        :returns: The position of row or None if not within selected set
        :rtype: int or None"""
        positions = []
        rows = self.get_selected_rows()
        for row in rows:
            pos = row.get_index()
            positions.append(pos)

        return self._model.get_position_for_id_in_range(text_id, positions)

    def do_grab_focus(self):
        Gtk.ListBox.do_grab_focus(self)
        row = self.get_selected_row()
        if row:
            GLib.idle_add(row.grab_focus)


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
        """Initialize a new DraftTextsList, without any items. Use ``set_model``
        for setting a model and populating view with items"""
        DraftBaseList.__init__(self)
        self.connect('key-press-event', self._on_key_press)

    def _create_row_widget(self, text_data, user_data):
        """Create a row widget for given text data (meant for internal usage)"""
        title = text_data.title
        subtitle = text_data.subtitle

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
        """Set label for the first child of ``box`` to ``title``

        :param box: A GtkBox whose first child is a GtkLabel
        :param title: A string to set the label with
        """
        labels = box.get_children()
        label = labels[0]
        label.set_markup('<b>%s</b>' % xml_escape(title))
        self._shape_row_label(label)

    def _append_subtitle_label(self, box, subtitle):
        """Set label for the second child of ``box`` to ``subtitle``

        :param box: A GtkBox whose second child is a GtkLabel
        :param subtitle: A string to set the label with
        """
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
        """Handler for signal ``key-press-event``"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            # Delete row and file with (Del)
            if event.keyval == Gdk.KEY_Delete:
                self.delete_selected()

    def _on_drag_begin(self, widget, drag_context):
        """Handler for ``drag-begin`` signal

        When drag action begins this function does several things:
            1. find the row for @widget,
            2. estimate the number of rows being moved
            3. unselect it (if selected)
            4. add a frame style for opaque background and borders
            5. create a cairo surface for row (if single), a text surface otherwise
            6. set it as icon for the drag context
            7. remove the frame style
            8. set the row as selected
        """
        row = widget.get_ancestor(Gtk.ListBoxRow.__gtype__)
        num_selected = len(self.get_selected_rows())
        if (not row.is_selected() and self.in_multi_selection_mode()):
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
        """Handler for ``drag-data-get`` signal

        Expects selection data containing the db id of the row being dragged
        """
        rows = self.get_selected_rows()
        positions = [row.get_index() for row in rows]
        text_data_list = [self._model.get_item(position)
                          for position in positions]
        ids = [text_data.id for text_data in text_data_list]

        selection.set(selection.get_target(), -1, bytearray(ids))
        self._texts_being_moved = ids

    def _on_text_viewed(self, widget, text_data):
        """Select the text in textlist for given text data

        :param widget: Widget on which event was triggered
        :param text_data: A TextRowData object associated with a text
        """
        if not hasattr(self, '_model'):
            return

        list_type, group, in_trash = self._model.get_model_attributes()
        if list_type == TextListType.GROUP_TEXTS:
            group_id = text_data.parent_id
            text_id = text_data.id
            self.text_view_selection_in_progress = True
            if group['id'] != text_data.parent_id:
                if in_trash and group_id is not None:
                    pos = self._model.get_position_for_id(text_id)
                    if pos is not None:
                        parent_group = self._model.get_parent_for_position(pos)
                        if parent_group and not parent_group['in_trash']:
                            group_id = None
                self.emit('selection-requested', group_id, text_id, in_trash)
            else:
                self.select_for_id(text_id)

    def _on_items_changed(self, model, position, removed, added):
        DraftBaseList.items_changed_base(self,
                                         model,
                                         position,
                                         removed,
                                         added)
        if not added or not removed:
            text_data = self._model.get_item(position)
            if not text_data:
                return

            title = text_data.title
            subtitle = text_data.subtitle
            self.set_title_for_position(position, title)
            self.set_subtitle_for_position(position, subtitle)

    def _connect_focus_based_styling(self, row):
        """For given row connect ``focus-in`` and ``focus-out`` handlers

        :param row: A GtkListBoxRow object
        """

        def on_row_unfocused(widget, cb_data=None):
            if not self.get_focus_child():
                self._set_focused_listview_class(True)

        def on_row_focused(widget, cb_data=None):
            self._set_focused_listview_class(False)

        row.connect('focus-out-event', on_row_unfocused)
        row.connect('focus-in-event', on_row_focused)

    @GObject.Property(type=GObject.TYPE_PYOBJECT)
    def editor(self):
        return DraftBaseList.editor.fget(self)

    @editor.setter
    def editor(self, editor):
        """Set editor and connect any other signal(s)."""
        DraftBaseList.editor.fset(self, editor)
        editor.connect('text-viewed', self._on_text_viewed)

    def set_model(self, collection_class=None, parent_group=None):
        """Set the model for the ListBox according to given parameters

        If a ``parent_group`` is provided, the model will contain the texts
        present within this group, otherwise the model will contain the texts
        contained within the given collection class. If neither is provided,
        all non-trashed texts are shown.

        :param collection_class: A collection class type
        :param parent_group: A dictionary representing some group metadata
        """
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

        # block handler before attempting rebind a new model
        with self.handler_block(self._row_selected_handler):
            with self.handler_block(self._rows_changed_handler):
                self.bind_model(self._model, self._create_row_widget, None)

        # register/re-register this only after a model has been bound
        self._items_changed_handler_id = self._model.connect('items-changed',
                                                             self._on_items_changed)

        self._set_focused_listview_class(True)

        # if the new model has some texts that were just moved within,
        # select these newly-moved texts so that the user knows them to be
        if self._texts_being_moved:
            self.set_multi_selection_mode(len(self._texts_being_moved) > 1)
            for row in self.get_children():
                position = row.get_index()
                row_data = self._model.get_item(position)
                if row_data.id in self._texts_being_moved:
                    GLib.idle_add(self.select_row, row)
                    if row_data.id == self._texts_being_moved[0]:
                        GLib.idle_add(self.scroll_to_row, row)
            self._texts_being_moved = []
        else:
            position = self._model.get_latest_modified_position()
            if position is not None:
                row = self.get_row_at_index(position)
                self.select_row(row)
                GLib.idle_add(self.scroll_to_row, row)

            for row in self.get_children():
                self._connect_focus_based_styling(row)

    def scroll_to_row(self, row):
        """Scroll to a given row

        :param row: A GtkListBoxRow
        """
        alloc = self.get_parent().get_allocation()
        adj = self.get_adjustment()
        current_y = adj.get_value()

        row_alloc = row.get_allocation()
        if row_alloc.y < current_y:
            adj.set_value(row_alloc.y)
        elif row_alloc.y > current_y + alloc.height:
            adj.set_value(row_alloc.y + row_alloc.height - alloc.height)

    def new_text_request(self):
        """Request for creation of a new text and append it to the list"""
        self._model.new_text_request()
        position = self._model.get_latest_modified_position()
        new_row = self.get_row_at_index(position)
        self._connect_focus_based_styling(new_row)
        self.select_row(new_row)
        self.emit('text-created')

        def scroll_to_new_row():
            adj = self.get_adjustment()
            adj.set_value(adj.get_upper())

        GLib.idle_add(scroll_to_new_row)

    def set_group_for_ids(self, text_ids, group):
        """Move texts to a given group

        Send texts with ids within the given ``text_ids`` list, to the group
        with id ``group``. Assuming this is not the same group as the texts is
        currently in, it will be removed from the selected model.

        :param text_ids: A list of valid text ids
        :param group: A valid group id to move the texts to"""
        for id in text_ids:
            position = self._model.get_position_for_id(id)
            if position is not None:
                item = self._model.get_item(position)
                item.parent_id = group
        self.emit('text-moved-to-group', group)

    def set_title_for_position(self, position, title):
        """Update title label

        :param position: Index position for which update is needed
        :param title: Title string to be set for label
        """
        row = self.get_row_at_index(position)
        box = row.get_child().get_child()
        self._set_title_label(box, title)
        self.emit('text-title-changed', title, "", False)

    def set_subtitle_for_position(self, position, subtitle):
        """Update subtitle label

        :param position: Index position for which update is needed
        :param title: Subtitle string to be set for label
        """
        row = self.get_row_at_index(position)
        box = row.get_child().get_child()
        self._append_subtitle_label(box, subtitle)

    def delete_selected(self, permanent=False):
        """Delete currently selected texts in the list

        :param permanent: If true, deletes those entries permanently from the db
        """
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
            item = self._model.get_item(position)
            item.in_trash = False

        self.set_multi_selection_mode(False)
        self.emit('text-restored')

    def selected_rows_will_be_orphaned(self):
        """Check if the currently selected row in list will be orphaned if we
        restore the text from trash"""
        count = 0
        selected_rows = self.get_selected_rows()
        for row in selected_rows:
            position = row.get_index()
            text = self._model.get_item(position)
            parent_group = self._model.get_parent_for_position(position)
            if parent_group and parent_group['in_trash']:
                count += 1
        return count

    def delete_rows(self, rows, permanent=False):
        """Delete rows and associated texts in the list. The texts are sent to
        trash or permanently deleted if the ``permanent`` parameter is ``True``

        :param permanent: If true, deletes those entries permanently from the db
        """
        for row in rows:
            position = row.get_index()
            if permanent:
                self._model.delete_item_at_postion_permanently(position)
            else:
                item = self._model.get_item(position)
                item.in_trash = True

    def delete_all_rows_permanently(self):
        """Delete all rows in ListBox and permanently delete the associated
        texts

        Helpful when we need to empty a group (for eg. emptying trash)
        """
        all_rows = self.get_children()
        with self.handler_block(self._row_selected_handler):
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
        """Create a row widget for given text data (meant for internal usage)"""
        title = text_data.title
        highlights = text_data.misc

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
        """Set label for the first child of ``box`` to ``title``

        :param box: A GtkBox whose first child is a GtkLabel
        :param title: A string to set the label with
        """
        labels = box.get_children()
        label = labels[0]
        label.set_markup('<b>%s</b>' % xml_escape(title))
        self._shape_row_label(label)

    def _append_highlights(self, box, highlights):
        """Append highlights to the row

        Be careful when using this method - both the parameters are expected to
        be of different structure depending on whether ``self`` is showing
        results for tag or content based search.

        :param box: A GtkBox having a situational second child as Box or Label
        :param highlights: A list of matched tags or a string of highlight markup
        """
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

    def set_model(self, results=None, tagged_results=False, trashed=False):
        """Set a model for this view according to the parameters

        If ``tagged_results`` is ``True`` then, a more appropriate kind of row
        highlights will be shown.

        :param results: A dictionary maaping text id to matches
        :param tagged_results: Whether this view will be showing tag-search results
        :param trashed: Whether the searched items are within trash
        """
        self._model = DraftTextListStore(list_type=TextListType.RESULT_TEXTS,
                                         results=results,
                                         trashed=trashed)
        self._showing_tagged_results = tagged_results
        self.bind_model(self._model, self._create_row_widget, None)
        self._items_changed_handler_id = self._model.connect('items-changed',
                                                             self._on_items_changed)

    @GObject.Property(type=GObject.TYPE_PYOBJECT)
    def editor(self):
        return self._editor

    @editor.setter
    def editor(self, editor):
        self._editor = editor
