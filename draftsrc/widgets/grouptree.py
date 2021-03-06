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

from gi.repository import Gtk, Pango, Gdk, GObject

from draftsrc.widgetmodels.grouptreestore import DraftGroupTreeStore, Column, GroupTreeType
from draftsrc.widgetmodels.collectionliststore import CollectionClassType
from draftsrc.widgets import TEXT_MOVE_INFO, TEXT_MOVE_TARGET
from draftsrc.widgets import GROUP_MOVE_INFO, GROUP_MOVE_TARGET


class DraftGroupTree(Gtk.TreeView):
    """The view presenting all the text groups in user's collection"""
    __gtype_name__ = 'DraftGroupTree'

    __gsignals__ = {
        'texts-dropped': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
        'group-selected': (GObject.SignalFlags.RUN_FIRST,
                           None,
                           (GObject.TYPE_PYOBJECT,)),
        'rename-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'menu-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'group-created': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'group-deleted': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'group-restored': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _group_column = None
    _tree_type = None

    def __repr__(self):
        return '<DraftGroupTree>'

    def __init__(self):
        Gtk.TreeView.__init__(self)
        ctx = self.get_style_context()
        ctx.add_class('draft-treeview')

        self.selection = self.get_selection()
        self.selection.connect('changed', self._on_selection_changed)
        self.set_headers_visible(False)
        self.set_enable_search(False)
        self.set_activate_on_single_click(False)

        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                      [GROUP_MOVE_TARGET],
                                      Gdk.DragAction.MOVE)
        self.enable_model_drag_dest([GROUP_MOVE_TARGET, TEXT_MOVE_TARGET],
                                    Gdk.DragAction.MOVE)

        self.connect('key-press-event', self._on_key_press)
        self.connect('button-press-event', self._on_button_press)
        self.connect('drag-data-get', self._drag_data_get)
        self.connect('drag-data-received', self._drag_data_received)
        self.connect('row-activated', self._on_row_activated)

    def _on_key_press(self, widget, event):
        """Handle key presses within the widget. Ignore some events that are not
        meant for root iter."""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)
        path_string = self.get_selected_path().to_string()

        if not event_and_modifiers:
            if self._tree_type != GroupTreeType.TRASHED_GROUPS:
                if event.keyval == Gdk.KEY_Delete and path_string != '0':
                    self.delete_selected_row()
                elif event.keyval == Gdk.KEY_F2 and path_string != '0':
                    self.emit('rename-requested')

    def _on_button_press(self, widget, event):
        """Handle key presses within the widget"""
        modifiers = Gtk.accelerator_get_default_mod_mask()
        modifiers = (event.state & modifiers)

        if not modifiers:
            if event.triggers_context_menu():
                self.emit('menu-requested')

    def _on_selection_changed(self, selection):
        """Handle selection change and subsequently emit `group-selected` signal"""
        model, treeiter = self.selection.get_selected()

        # if this is only a group creation entry (decoy), do nothing
        if model and treeiter and not model[treeiter][Column.CREATED]:
            return

        if not (model and treeiter):
            return

        path = model.get_path(treeiter)
        group = model.get_group_for_iter(treeiter)
        self.emit('group-selected', group)

    def _on_row_activated(self, widget, path, column):
        self.toggle_expand_path(path)

    def do_drag_motion(self, context, x, y, time):
        """Override the default drag motion method and highlight with
        INTO_OR_AFTER move scheme"""
        if self._tree_type == GroupTreeType.TRASHED_GROUPS:
            return

        propagate = Gtk.TreeView.do_drag_motion(self, context, x, y, time)
        res = self.get_path_at_pos(x, y)
        if res:
            path, col, _x, _y = res
            selected_path = self.get_selected_path()
            if not selected_path or path.to_string() == selected_path.to_string():
                self.set_drag_dest_row(None,
                                       Gtk.TreeViewDropPosition.INTO_OR_AFTER)
                return False

            self.set_drag_dest_row(path, Gtk.TreeViewDropPosition.INTO_OR_AFTER)

        return propagate

    def _drag_data_get(self, widget, drag_context, sel, info, time):
        """Handle `drag-data-get` signal. Supply selection data with db id of
        row being dragged"""
        if self._tree_type == GroupTreeType.TRASHED_GROUPS:
            return

        path_string = self.get_selected_path().to_string()
        sel.set(sel.get_target(), -1, path_string.encode())

    def _drag_data_received(self, widget, drag_context, x, y, sel, info, time):
        """Handle `drag-data-received` signal. Obtain from selection data, the
        id for the row being dragged"""
        if self._tree_type == GroupTreeType.TRASHED_GROUPS:
            return

        model = self.get_model()
        res = self.get_path_at_pos(x, y)
        new_parent_iter = None
        new_parent_id = None
        if res:
            path, col, _x, _y = res
            new_parent_iter = model.get_iter(path)
            if not path.to_string() == '0':
                new_parent_id = model[new_parent_iter][Column.ID]

        if new_parent_iter is None:
            return

        if info == GROUP_MOVE_INFO:
            datum = sel.get_data()
            path_string = datum.decode()
            path = Gtk.TreePath.new_from_string(path_string)
            dragged_iter = model.get_iter(path)
            treeiter = model.move_to_group(dragged_iter, new_parent_iter)
            if treeiter:
                self.selection.select_iter(treeiter)
        elif info == TEXT_MOVE_INFO:
            data = sel.get_data()
            text_ids = list(data)
            self.emit('texts-dropped', text_ids, new_parent_id)

    def set_collection_model(self):
        tree_type = GroupTreeType.COLLECTION_GROUPS
        top_row_name=_("Local")
        self._set_model_with_type(tree_type, top_row_name)
        root_path = self._root_path()
        self.expand_row(root_path, False)

    def set_trash_model(self):
        tree_type = GroupTreeType.TRASHED_GROUPS
        top_row_name = _("Trash")
        self._set_model_with_type(tree_type, top_row_name)

    def _set_model_with_type(self, tree_type, top_row_name):
        model = DraftGroupTreeStore(tree_type, top_row_name)
        self.set_model(model)
        self._tree_type = tree_type
        if self._group_column:
            self.remove_column(self._group_column)
        self._populate()

    def _populate(self):
        """Set up cell renderer and column for the tree view and expand the
        top level row"""
        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        renderer.set_fixed_size(-1, 28)
        column = Gtk.TreeViewColumn(_("Groups"), renderer, text=Column.NAME)
        self._group_column = column
        self.append_column(column)
        self._group_column.set_expand(True)

    def _root_path(self):
        """Get the GtkTreePath for root entry of a treeview"""
        return Gtk.TreePath.new_from_string('0')

    def toggle_expand_path(self, path):
        if self.row_expanded(path):
            self.collapse_row(path)
        else:
            self.expand_row(path, False)

    def get_selected_path(self):
        model, treeiter = self.selection.get_selected()
        if model and treeiter:
            return model.get_path(treeiter)
        return None

    def get_selected_rect(self):
        path = self.get_selected_path()
        return self.get_cell_area(path, self._group_column)

    def set_faded_selection(self, faded):
        """Applies or removes the `draft-faded-selection` class to TreeView,
        useful when trying to visually denote the selected row as partially
        present"""
        faded_class = 'draft-faded-treeview'
        ctx = self.get_style_context()
        if faded:
            ctx.remove_class('draft-treeview')
            ctx.add_class(faded_class)
        elif ctx.has_class(faded_class):
            ctx.remove_class(faded_class)
            ctx.add_class('draft-treeview')

    def new_group_request(self):
        """Instruct model to create a new group and then return the GdkRectangle
        associated with the new cell created for this entry"""
        model, treeiter = self.selection.get_selected()
        new_iter = model.create_decoy_group(treeiter)

        self.expand_row(model.get_path(treeiter), False)
        self.selection.select_iter(new_iter)

    def finalize_name_for_new_group(self, name):
        """Give the selected group a name and then finalize its creation and
        if name is not a non-whitespace string, discard the row altogether"""
        model, treeiter = self.selection.get_selected()

        # check group has not yet been created
        assert not model[treeiter][Column.CREATED]

        group = model.finalize_group_creation(treeiter, name)
        self.emit('group-selected', group)
        self.emit('group-created')

    def discard_new_group(self):
        """Discard a currently selected group only if it is a decoy"""
        model, treeiter = self.selection.get_selected()

        # if group has been created do nothing
        if model[treeiter][Column.CREATED]:
            return

        parent = model.iter_parent(treeiter)
        model.remove(treeiter)
        if parent:
            self.selection.select_iter(parent)
        else:
            self.selection.select_path(self._root_path())

    def set_name_for_current_selection(self, name):
        """Change name for the group under current selection"""
        model, treeiter = self.selection.get_selected()
        model.set_prop_for_iter(treeiter, 'name', name)

    def selected_row_can_expand(self):
        """Check if selected row is capable of being expanded, i.e., has
        children"""
        num_groups, num_texts = self.count_groups_and_texts_for_selection()
        if num_groups:
            return True
        return False

    def selected_row_is_expanded(self):
        """Check if selected path is expanded or not"""
        path = self.get_selected_path()
        if self.row_expanded(path):
            return True
        return False

    def activate_selected_row(self):
        """Activates a the currently selected row"""
        path = self.get_selected_path()
        self.toggle_expand_path(path)

    def delete_selected_row(self, permanent=False):
        """Delete the group under selection"""
        model, treeiter = self.selection.get_selected()
        if permanent and model.tree_type == GroupTreeType.TRASHED_GROUPS:
            model.permanently_delete_group_at_iter(treeiter)
        else:
            model.set_prop_for_iter(treeiter, 'in_trash', True)

        self.emit('group-deleted')

    def delete_all_groups_permanently(self):
        """Delete all immediate children from a trash model and therefore
        deleting every group and and their texts in trash"""
        model = self.get_model()
        if model.tree_type == GroupTreeType.TRASHED_GROUPS:
            root_iter = model.get_iter_first()
            while model.iter_has_child(root_iter):
                treeiter = model.iter_children(root_iter)
                model.permanently_delete_group_at_iter(treeiter)

    def restore_selected_row(self):
        """Restore selected row from trash"""
        model, treeiter = self.selection.get_selected()
        if not model.tree_type == GroupTreeType.TRASHED_GROUPS:
            return

        model.set_prop_for_iter(treeiter, 'in_trash', False)
        self.emit('group-restored')

    def selected_row_will_be_orphaned(self):
        """Check whether the selected row will be orphaned if it is restored
        from trash"""
        model, treeiter = self.selection.get_selected()
        group = model.get_group_for_iter(treeiter)
        if group['parent_id'] is not None:
            return True
        return False

    def select_for_id(self, group_id):
        """Select a group for the given group id"""
        model = self.get_model()
        if group_id is None:
            self.select_top_level()
            return

        def select_if_group_id_matches(model, path, treeiter, data):
            if model[treeiter][Column.ID] == group_id:
                self.expand_to_path(path)
                self.selection.select_path(path)
                return True

            return False

        model.foreach(select_if_group_id_matches, None)

    def select_top_level(self):
        """Selects the top level root node. This can be helpful for selecting
        one node that we know will be present always (hopefully)"""
        model = self.get_model()
        self.selection.select_path(self._root_path())

    def select_group_with_last_modified_text(self):
        """Select a group for last modified text, otherwise select top node."""
        model = self.get_model()
        group_id = model.get_last_modified_parent_id()
        self.select_for_id(group_id)
        self.grab_focus()
        model, treeiter = self.selection.get_selected()
        return model.get_group_for_iter(treeiter)

    def count_top_level_groups_and_texts(self):
        """Count the number of groups and texts in the root node"""
        model = self.get_model()
        treeiter = model.get_iter(self._root_path())
        num_groups = model.count_groups_for_iter(treeiter)
        num_texts = model.count_texts_for_iter(treeiter)
        return num_groups, num_texts

    def count_groups_and_texts_for_selection(self):
        """Count the number of groups and texts in the currently selected group"""
        model, treeiter = self.selection.get_selected()
        if treeiter is None:
            treeiter = model.get_iter(self._root_path())
        num_groups = model.count_groups_for_iter(treeiter)
        num_texts = model.count_texts_for_iter(treeiter)
        return num_groups, num_texts

    def has_row_selected(self):
        """Check if a row has been selected in the treeview"""
        model, treeiter = self.selection.get_selected()
        if treeiter is None:
            return False

        return True

    def has_top_level_row_selected(self):
        """Check if top level row is selected in view"""
        model, treeiter = self.selection.get_selected()
        if treeiter is None:
            return False

        if model.get_path(treeiter) == self._root_path():
            return True

        return False

    def get_group_for_selected(self):
        """Return metadata as a dict for the selected group."""
        model, treeiter = self.selection.get_selected()
        return model.get_group_for_iter(treeiter)

    def _bottom_most_iter(self):
        """Get the last visible iterator in the treeview."""
        model = self.get_model()
        last = model[-1]
        last_iter = last.iter
        last_path = last.path
        while (model.iter_has_child(last_iter)
                and self.row_expanded(last_path)):
            last_index = model.iter_n_children(last.iter) - 1
            last_iter = model.iter_nth_child(last_iter,
                                                   last_index)
            last_path = model.get_path(last_iter)

        return last_iter

    def should_move_down(self):
        """Whether the widget has reached the last visible node and should move
        down to the next widget."""
        model, treeiter = self.selection.get_selected()
        last_iter = self._bottom_most_iter()
        return model.get_path(treeiter) == model.get_path(last_iter)

    def should_move_up(self):
        """Whether the widget has reach the top most node and should move up to
        the previous widget."""
        model, treeiter = self.selection.get_selected()
        top = self._root_path()
        return model.get_path(treeiter) == top

    def focus_top_level(self):
        """Selects and focuses on the top node."""
        self.set_cursor(self._root_path(), None, False)

    def focus_bottom_level(self):
        """Selects and focuses on the bottom-most visible node."""
        model = self.get_model()
        last_iter = self._bottom_most_iter()
        last_path = model.get_path(last_iter)
        self.set_cursor(last_path, None, False)
