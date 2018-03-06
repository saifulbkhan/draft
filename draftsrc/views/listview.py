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

from gettext import gettext as _

from gi.repository import Gtk, GLib, Pango, Gdk, GObject

from draftsrc.views.store import DraftListStore, DraftTreeStore, Column


class GroupTreeView(Gtk.Bin):
    """A container bounding a GtkTreeView that allows for slider based hiding
    and resizing"""
    _creation_state = False

    def __repr__(self):
        return '<GroupTreeView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Draft/grouptreeview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.slider = self.builder.get_object('slider')
        self.slider.set_hexpand(False)
        scrolled = self.builder.get_object('scrolled')

        self.add(self.slider)
        self.view = DraftGroupsView()
        scrolled.add(self.view)

        self._popover = self.builder.get_object('popover')
        self._popover_title = self.builder.get_object('popover_title')
        self._name_entry = self.builder.get_object('text_entry')
        self._action_button = self.builder.get_object('action_button')

        self.view.connect('group-selected', self._on_group_selected)
        self.view.connect('rename-requested', self._on_group_rename_requested)
        self._action_button.connect('clicked', self._on_name_set)
        self._name_entry.connect('activate', self._on_name_set)
        self._name_entry.connect('changed', self._on_name_entry_changed)
        self._popover.connect('closed', self._on_popover_closed)

    def _on_group_selected(self, widget, group):
        """Handler for `group-selected` signal from DraftsTreeView. Calls on
        TextListView to reload its model with texts from selected group"""
        self.parent_window.textlistview.set_model_for_group(group)

    def toggle_panel(self):
        """Toggle the reveal status of slider's child"""
        if self.slider.get_reveal_child():
            self.slider.set_reveal_child(False)
        else:
            self.slider.set_reveal_child(True)

    def new_group_request(self):
        """Cater to the request for new group creation. Pops up an entry to set
        the name of the new group as well"""
        rect = self.view.new_group_request()
        self.view.set_faded_selection(True)

        self._creation_state = True
        self._action_button.set_label('Create')
        self._popover_title.set_label('Group Name')
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _on_name_entry_changed(self, widget):
        """Adjust the sensitivity of action button depending on the content of
        text entry"""
        text = self._name_entry.get_text()
        activate = bool(text.strip())
        self._action_button.set_sensitive(activate)

    def _on_name_set(self, widget):
        """Handler for activation of group naming entry or click of action
        button. Obtains the string from text entry and set that as the name of
        the group"""
        name = self._name_entry.get_text().strip()
        if not name:
            return

        if self._creation_state:
            self.view.finalize_name_for_new_group(name)
        else:
            self.view.set_name_for_current_selection(name.strip())

        self._popover.popdown()

    def _on_popover_closed(self, widget):
        """When the naming popover closes, discard new group if it has not been
        finalized, set creation state to `False` and set name entry to blank"""
        self._name_entry.set_text('')
        self.view.discard_new_group()
        self.view.set_faded_selection(False)
        self._creation_state = False

    def _on_group_rename_requested(self, widget, rect):
        """Handle request for group rename, set button and popover title"""
        self._action_button.set_label('Rename')
        self._popover_title.set_label('Rename Group')
        self._popover.set_pointing_to(rect)
        self._popover.popup()


class DraftGroupsView(Gtk.TreeView):
    """The view presenting all the text groups in user's collection"""
    __gtype_name__ = 'DraftGroupsView'

    __gsignals__ = {
        'group-selected': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'rename-requested': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,))
    }

    def __repr__(self):
        return '<DraftGroupsView>'

    def __init__(self):
        Gtk.TreeView.__init__(self, DraftTreeStore(top_row_name='Local'))
        ctx = self.get_style_context()
        ctx.add_class('draft-treeview')

        self.selection = self.get_selection()
        self.selection.connect('changed', self._on_selection_changed)

        self._populate()
        self.set_headers_visible(False)
        self.connect('key-press-event', self._on_key_press)

    def _on_key_press(self, widget, event):
        """Handle key presses within the widget"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            # Delete row and file with (Del)
            if event.keyval == Gdk.KEY_Delete:
                self.delete_selected_row()
            elif event.keyval == Gdk.KEY_F2:
                model, treeiter = self.selection.get_selected()
                path = model.get_path(treeiter)
                rect = self.get_cell_area(path, self.title)
                self.emit('rename-requested', rect)

    def _populate(self):
        """Set up cell renderer and column for the tree view and expand the
        top level row"""
        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        renderer.set_fixed_size(-1, 28)
        column = Gtk.TreeViewColumn('title', renderer, text=Column.NAME)
        self.title = column
        self.append_column(column)
        self.title.set_expand(True)
        root_path = self._root_path()
        self.expand_row(root_path, False)

    def _root_path(self):
        """Get the GtkTreePath for root entry of a treeview"""
        return Gtk.TreePath.new_from_string('0')

    def _on_selection_changed(self, selection):
        """Handle selection change and subsequently emit `group-selected` signal"""
        model, treeiter = self.selection.get_selected()
        if not (model and treeiter):
            root_path = self._root_path()
            self.selection.select_path(root_path)
            return

        path = model.get_path(treeiter)
        self.expand_row(path, False)
        group = model.get_group_for_iter(treeiter)
        self.emit('group-selected', group)

    def set_faded_selection(self, faded):
        """Applies or removes the `draft-faded-selection` class to TreeView,
        useful when trying to visually denote the selected row as partially
        present"""
        faded_class = 'draft-faded-selection'
        ctx = self.get_style_context()
        if faded:
            ctx.add_class(faded_class)
        elif ctx.has_class(faded_class):
            ctx.remove_class(faded_class)

    def new_group_request(self):
        """Instruct model to create a new group and then return the GdkRectangle
        associated with the new cell created for this entry"""
        model, treeiter = self.selection.get_selected()
        new_iter = model.create_decoy_group(treeiter)

        self.expand_row(model.get_path(treeiter), False)
        self.selection.select_iter(new_iter)

        path = model.get_path(new_iter)
        rect = self.get_cell_area(path, self.title)
        return rect

    def finalize_name_for_new_group(self, name):
        """Give the selected group a name and then finalize its creation and
        if name is not a non-whitespace string, discard the row altogether"""
        model, treeiter = self.selection.get_selected()

        # check group has not yet been created
        assert not model[treeiter][Column.CREATED]

        model.finalize_group_creation(treeiter, name)

    def discard_new_group(self):
        """Discard a currently selected group only if it is a decoy"""
        model, treeiter = self.selection.get_selected()

        # if group has been created do nothing
        if model[treeiter][Column.CREATED]:
            return

        parent = model.iter_parent(treeiter)
        model.remove(treeiter)
        self.selection.select_iter(parent)

    def set_name_for_current_selection(self, name):
        """Change name for the group under current selection"""
        model, treeiter = self.selection.get_selected()
        model.set_prop_for_iter(treeiter, 'name', name)

    def delete_selected_row(self, permanent=False):
        """Delete the group under selection"""
        model, treeiter = self.selection.get_selected()
        if not permanent:
            model.set_prop_for_iter(treeiter, 'in_trash', True)
        else:
            model.permanently_delete_group_at_iter(treeiter)


# TODO: Make this a stack for storing multiple DraftTextsList
class TextListView(Gtk.Bin):
    sidebar_width = 250
    def __repr__(self):
        return '<TextListView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Draft/textlistview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.slider = self.builder.get_object('slider')
        self.slider.set_hexpand(False)
        textslist = self.builder.get_object('textslist')
        listview = self.builder.get_object('listview')

        self.add(self.slider)
        self.view = DraftTextsList()
        listview.add(self.view)

        self.search_bar = self.builder.get_object('search_bar')
        self.search_entry = self.builder.get_object('search_entry')

    def toggle_panel(self):
        if self.slider.get_reveal_child():
            self.slider.set_reveal_child(False)
        else:
            self.slider.set_reveal_child(True)

    def search_toggled(self):
        if self.search_bar.get_search_mode():
            self.search_bar.set_search_mode(False)
            self.search_entry.set_text("")
        else:
            self.search_bar.set_search_mode(True)
            self.search_entry.grab_focus()

    def set_model_for_group(self, group):
        self.view.set_model(group)

    def set_editor(self, editor):
        self.view.set_editor(editor)

    def new_text_request(self):
        self.view.new_text_request()


class DraftTextsList(Gtk.ListBox):
    """The listbox containing all the texts in a text group"""
    __gtype__name__ = 'DraftTextsList'

    def __repr__(self):
        return '<DraftTextsList>'

    def __init__(self):
        """Initialize a new DraftTextsList for given @parent_group

        @parent_group: string, unique hash string for @parent_group
        """
        Gtk.ListBox.__init__(self)
        self.connect('key-press-event', self._on_key_press)
        self.connect('row-selected', self._on_row_selected)

    def _create_row_widget(self, text_data, user_data):
        """Create a row widget for @text_data"""
        data_dict = text_data.to_dict()
        title = data_dict['title']
        subtitle = data_dict['subtitle']

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row_box.set_spacing(2)
        for direction in ['left', 'right', 'top', 'bottom']:
            method = 'set_margin_%s' % direction
            getattr(row_box, method)(6)

        title_label = Gtk.Label()
        row_box.pack_start(title_label, True, False, 0)

        self._set_title_label(row_box, title)
        self._append_subtitle_label(row_box, subtitle)

        return row_box

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

    def _on_row_selected(self, widget, row):
        """Handler for signal `row-selected`"""
        if not row:
            return

        position = row.get_index()
        self._model.prepare_for_edit(position,
                                    self.editor.switch_view,
                                    self.editor.load_file)

    def _on_items_changed(self, model, position, removed, added):
        """Handler for model's `items-changed` signal"""
        row = self.get_row_at_index(position)
        self.select_row(row)

    def set_model(self, parent_group):
        self._model = DraftListStore(parent_group)
        self.bind_model(self._model, self._create_row_widget, None)
        self._model.connect('items-changed', self._on_items_changed)

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
        editor.connect('keywords-changed', self.set_keywords_for_current_selection)
        editor.connect('view-changed', self.save_last_edit_data)

    def new_text_request(self):
        """Request for creation of a new text and append it to the list"""
        self._model.new_text_request()

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

        box = row.get_child()
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

        box = row.get_child()
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

    def set_keywords_for_current_selection(self, widget, keywords):
        """Ask store to make changes to the keywords of the currently selected text
        so that it can be written to db.

        @self: DraftTextsList
        @keywords: list, the list of string keywords which the selected text will be
               tagged with.
        """
        row = self.get_selected_row()
        position = row.get_index()
        new_keywords = self._model.set_keywords_for_position(position, keywords)

        # since @new_keywords might have slightly different letter case keywords, we
        # should re-update editor keywords as well and then update statusbar, though
        # this is probably not the best place to do it.
        self.editor.current_text_data['keywords'] = new_keywords
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
