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

from gi.repository import Gtk, GLib, Gdk

from draftsrc import export
from draftsrc.widgets.collectionlist import DraftCollectionList
from draftsrc.widgets.grouptree import DraftGroupTree


class DraftLibraryView(Gtk.Bin):
    """A container bounding a GtkTreeView that allows for slider based hiding
    and resizing"""
    collection_class_selected = None
    panel_visible = True
    _creation_state = False

    def __repr__(self):
        return '<DraftLibraryView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Draft/librarypanelview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.slider = self.builder.get_object('slider')
        self.slider.set_hexpand(False)
        self.add(self.slider)

        collection_box = self.builder.get_object('collection_box')
        separator = self.builder.get_object('library_separator')

        label = Gtk.Label()
        library_title = _("Library")
        label.set_label(library_title)
        label.set_halign(Gtk.Align.START)
        ctx = label.get_style_context()
        ctx.add_class('draft-tree-title')
        collection_box.pack_start(label, False, False, 0)

        self.collection_list = DraftCollectionList()
        collection_box.pack_start(self.collection_list, False, True, 0)

        self.trash_view = DraftGroupTree()
        self.trash_view.set_trash_model()
        collection_box.pack_start(self.trash_view, False, True, 0)

        collection_box.pack_start(separator, False, True, 0)

        label = Gtk.Label()
        groups_title =_("Groups")
        label.set_label(groups_title)
        label.set_halign(Gtk.Align.START)
        ctx = label.get_style_context()
        ctx.add_class('draft-tree-title')
        collection_box.pack_start(label, False, False, 0)

        self.local_groups_view = DraftGroupTree()
        self.local_groups_view.set_collection_model()
        collection_box.pack_start(self.local_groups_view, False, True, 0)

        self._popover = self.builder.get_object('popover')
        self._popover_title = self.builder.get_object('popover_title')
        self._name_entry = self.builder.get_object('text_entry')
        self._action_button = self.builder.get_object('action_button')

        self._popover_menu = self.builder.get_object('popover_menu')
        self._new_group_button = self.builder.get_object('group_button')
        self._sub_group_button = self.builder.get_object('subgroup_button')
        self._rename_button = self.builder.get_object('rename_button')
        self._remove_button = self.builder.get_object('remove_button')
        self._expand_button = self.builder.get_object('expand_button')
        self._collapse_button = self.builder.get_object('collapse_button')
        self._export_html_button = self.builder.get_object('export_html_button')

        self._trash_menu = self.builder.get_object('trash_popover_menu')
        self._restore_button = self.builder.get_object('trash_restore_button')
        self._delete_button = self.builder.get_object('trash_delete_button')
        self._empty_trash_button = self.builder.get_object('empty_trash_button')
        self._trash_expand_button = self.builder.get_object('trash_expand_button')
        self._trash_collapse_button = self.builder.get_object('trash_collapse_button')

        self.collection_list.connect('class-selected',
                                  self._on_collection_class_selected)
        self.collection_list.connect('key-press-event', self._on_collection_list_key_press)

        self.local_groups_view.connect('group-selected', self._on_group_selected)
        self.local_groups_view.connect('texts-dropped', self._on_texts_dropped)
        self.local_groups_view.connect('rename-requested', self._on_group_rename_requested)
        self.local_groups_view.connect('menu-requested', self._on_group_menu_requested)
        self.local_groups_view.connect('group-created', self._on_group_created)
        self.local_groups_view.connect('group-deleted', self._on_group_deleted)
        self.local_groups_view.connect('key-press-event', self._on_local_view_key_press)

        self.trash_view.connect('group-selected', self._on_group_selected)
        self.trash_view.connect('group-restored', self._on_group_restored)
        self.trash_view.connect('menu-requested', self._on_trash_menu_requested)
        self.trash_view.connect('key-press-event', self._on_trash_view_key_press)

        self._action_button.connect('clicked', self._on_name_set)
        self._name_entry.connect('activate', self._on_name_set)
        self._name_entry.connect('changed', self._on_name_entry_changed)
        self._popover.connect('closed', self._on_popover_closed)
        self._rename_button.connect('clicked', self._on_rename_clicked)
        self._remove_button.connect('clicked', self._on_remove_clicked)
        self._expand_button.connect('clicked', self._on_expand_clicked)
        self._collapse_button.connect('clicked', self._on_expand_clicked)
        self._restore_button.connect('clicked', self._on_restore_clicked)
        self._delete_button.connect('clicked', self._on_delete_clicked)
        self._empty_trash_button.connect('clicked', self._on_empty_trash_button_clicked)
        self._trash_expand_button.connect('clicked', self._on_trash_expand_clicked)
        self._trash_collapse_button.connect('clicked', self._on_trash_expand_clicked)
        self._export_html_button.connect('clicked', self._on_export_html_clicked)

    def _on_collection_class_selected(self, widget, collection_class_type):
        """Handler for `class-selected` signal from DraftsCollectionView. Calls
        TextListView to update its collection class and consequently its model"""
        self.parent_window.textlistview.set_collection_class_type(collection_class_type)
        self.local_groups_view.selection.unselect_all()
        self.trash_view.selection.unselect_all()
        self.collection_class_selected = collection_class_type
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_selected(self, widget, group):
        """Handler for `group-selected` signal from DraftsTreeView. Calls on
        TextListView to reload its model with texts from selected group"""
        self.collection_list.selection.unselect_all()
        self.collection_class_selected = None

        if widget == self.local_groups_view:
            self.trash_view.selection.unselect_all()
        elif widget == self.trash_view:
            self.local_groups_view.selection.unselect_all()

        self.parent_window.update_content_view_and_headerbar()
        self.parent_window.textlistview.set_model_for_group(group)

    def _on_collection_list_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_Down and widget.should_move_down():
                self.trash_view.focus_top_level()
                self.trash_view.grab_focus()
            elif (event.keyval == Gdk.KEY_Right
                    and self.parent_window.textlistview.panel_visible):
                self.parent_window.textlistview.view.grab_focus()

    def _on_local_view_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_Up and widget.should_move_up():
                self.trash_view.focus_bottom_level()
                self.trash_view.grab_focus()
            elif (event.keyval == Gdk.KEY_Right
                    and self.parent_window.textlistview.panel_visible):
                self.parent_window.textlistview.view.grab_focus()

    def _on_trash_view_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_Down and widget.should_move_down():
                self.local_groups_view.focus_top_level()
                self.local_groups_view.grab_focus()
            elif event.keyval == Gdk.KEY_Up and widget.should_move_up():
                self.collection_list.focus_bottom_level()
                self.collection_list.grab_focus()
            elif (event.keyval == Gdk.KEY_Right
                    and self.parent_window.textlistview.panel_visible):
                self.parent_window.textlistview.view.grab_focus()

    def _on_texts_dropped(self, widget, text_ids, new_parent_id):
        """Handle view's `texts-dropped` signal"""
        self.parent_window.textlistview.set_group_for_texts(text_ids,
                                                            new_parent_id)

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
            self.local_groups_view.finalize_name_for_new_group(name)
        else:
            self.local_groups_view.set_name_for_current_selection(name.strip())

        self._popover.popdown()

    def _on_popover_closed(self, widget):
        """When the naming popover closes, discard new group if it has not been
        finalized, set creation state to `False` and set name entry to blank"""
        self._name_entry.set_text('')
        self.local_groups_view.discard_new_group()
        self.local_groups_view.set_faded_selection(False)
        self._creation_state = False

    def _on_group_rename_requested(self, widget):
        """Handle request for group rename, set button and popover title"""
        rect = self.local_groups_view.get_selected_rect()
        self._action_button.set_label('Rename')
        self._popover_title.set_label('Rename Group')
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _on_group_created(self, widget):
        """Handle view's `group-created` signal"""
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_deleted(self, widget):
        """Handle view's `group-deleted` signal"""
        self.trash_view.set_trash_model()
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_restored(self, widget):
        """Handle trash view's `group-restored` signal"""
        self.local_groups_view.set_collection_model()
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_menu_requested(self, widget):
        """Cater to context menu request for a group. Ignore if the selection
        is the root container."""

        def popup_menu():
            if self.local_groups_view.has_top_level_row_selected():
                self._new_group_button.set_visible(True)
                self._sub_group_button.set_visible(False)
                self._rename_button.set_sensitive(False)
                self._remove_button.set_sensitive(False)
            else:
                self._sub_group_button.set_visible(True)
                self._new_group_button.set_visible(False)
                self._rename_button.set_sensitive(True)
                self._remove_button.set_sensitive(True)

            rect = self.local_groups_view.get_selected_rect()
            self._popover_menu.set_relative_to(self.local_groups_view)
            self._popover_menu.set_pointing_to(rect)
            self._popover_menu.popup()

            if not self.local_groups_view.selected_row_can_expand():
                self._expand_button.set_sensitive(False)
                self._collapse_button.set_sensitive(False)
            elif self.local_groups_view.selected_row_is_expanded():
                self._expand_button.set_sensitive(False)
                self._collapse_button.set_sensitive(True)
            else:
                self._expand_button.set_sensitive(True)
                self._collapse_button.set_sensitive(False)

        # have to queue this in main loop, so that correct GdkRectangle is
        # selected before making menu point to it.
        GLib.idle_add(popup_menu)

    def _on_expand_clicked(self, widget):
        self.local_groups_view.activate_selected_row()

    def _on_rename_clicked(self, widget):
        self.local_groups_view.emit('rename-requested')
        self._popover_menu.popdown()

    def _on_remove_clicked(self, widget):
        self.local_groups_view.delete_selected_row()
        self._popover_menu.popdown()

    def _on_export_html_clicked(self, widget):
        group = self.local_groups_view.get_group_for_selected()
        export.request_save_html_for_group(group)

    def _on_trash_menu_requested(self, widget):
        """Cater to context menu request for a trashed group. Ignore if the
        selection is the root container."""

        def popup_menu():
            if self.trash_view.has_top_level_row_selected():
                self._empty_trash_button.set_visible(True)
                self._delete_button.set_visible(False)
                self._restore_button.set_visible(False)
            else:
                self._empty_trash_button.set_visible(False)
                self._delete_button.set_visible(True)
                self._restore_button.set_visible(True)

            if not self.trash_view.selected_row_can_expand():
                self._trash_expand_button.set_sensitive(False)
                self._trash_collapse_button.set_sensitive(False)
            elif self.trash_view.selected_row_is_expanded():
                self._trash_expand_button.set_sensitive(False)
                self._trash_collapse_button.set_sensitive(True)
            else:
                self._trash_expand_button.set_sensitive(True)
                self._trash_collapse_button.set_sensitive(False)

            rect = self.trash_view.get_selected_rect()
            self._trash_menu.set_relative_to(self.trash_view)
            self._trash_menu.set_pointing_to(rect)
            self._trash_menu.popup()

        # have to queue this in main loop, so that correct GdkRectangle is
        # selected before making menu point to it.
        GLib.idle_add(popup_menu)

    def _on_delete_clicked(self, widget):
        dialog = self.parent_window.bring_up_final_deletion_dialog()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.trash_view.delete_selected_row(permanent=True)
        dialog.destroy()
        self._popover_menu.popdown()

    def _on_restore_clicked(self, widget):
        if self.trash_view.selected_row_will_be_orphaned():
            dialog = self.parent_window.bring_up_orphan_restore_dialog()
            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                self.trash_view.restore_selected_row()
            dialog.destroy()
        else:
            self.trash_view.restore_selected_row()
        self._popover_menu.popdown()

    def _on_trash_expand_clicked(self, widget):
        self.trash_view.activate_selected_row()

    def _on_empty_trash_button_clicked(self, widget):
        dialog = self.parent_window.bring_up_emptying_trash_dialog()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.trash_view.delete_all_groups_permanently()
            self.trash_view.select_top_level()
            self.parent_window.textlistview.delete_all_texts_permanently()
            self.parent_window.update_content_view_and_headerbar()
        dialog.destroy()

    def toggle_panel(self):
        """Toggle the reveal status of slider's child"""
        if self.panel_visible:
            self.hide_panel()
        else:
            self.reveal_panel()

    def hide_panel(self):
        """Hide the slider's child"""
        self.slider.set_reveal_child(False)
        self.panel_visible = False

    def reveal_panel(self):
        """Reveal the slider's child"""
        self.slider.set_reveal_child(True)
        self.panel_visible = True

    def new_group_request(self):
        """Cater to the request for new group creation. Pops up an entry to set
        the name of the new group as well"""
        # use parent's reveal method to ensure size group allotment
        self.parent_window.reveal_library_panel(override_lock=True)

        self.local_groups_view.new_group_request()
        self.local_groups_view.set_faded_selection(True)

        def prepare_for_popup():
            rect = self.local_groups_view.get_selected_rect()
            self._action_button.set_label('Create')
            self._popover_title.set_label('Group Name')
            self._popover.set_relative_to(self.local_groups_view)
            self._popover.set_pointing_to(rect)
            self._popover.popup()

        self._creation_state = True
        GLib.idle_add(prepare_for_popup)

    def selection_request(self, group_id, in_trash=False):
        if in_trash:
            self.trash_view.select_for_id(group_id)
        else:
            self.local_groups_view.select_for_id(group_id)

    def escape_selection_mode(self):
        pass

    def collection_is_empty(self):
        """Check if there are any groups or texts present in the collection"""
        num_groups, num_texts = self.local_groups_view.count_top_level_groups_and_texts()
        if num_groups or num_texts:
            return False

        return True

    def trash_is_empty(self):
        """Checks whether there are any items in trash"""
        num_groups, num_texts = self.trash_view.count_top_level_groups_and_texts()
        if num_groups or num_texts:
            return False

        return True

    def trash_has_no_texts(self):
        """Checks if trash's top level has any texts in it or not"""
        num_groups, num_texts = self.trash_view.count_top_level_groups_and_texts()
        if num_texts:
            return False

        return True

    def selected_group_has_no_texts(self):
        """Check if selected group has any texts"""
        view = self.local_groups_view
        if self.selected_group_is_in_trash():
            view = self.trash_view
        num_groups, num_texts = view.count_groups_and_texts_for_selection()
        if num_texts:
            return False

        return True

    def selected_group_is_in_trash(self):
        """Check if selected item in panelview is in trash view"""
        if self.trash_view.has_row_selected():
            return True

        return False

    def selected_group_is_top_level(self):
        """Check if the top level group is selected"""
        view = self.local_groups_view
        if self.selected_group_is_in_trash():
            view = self.trash_view

        return view.has_top_level_row_selected()

    def select_appropriate_row(self):
        """Select an appropriate row in the library"""
        group = self.local_groups_view.select_group_with_last_modified_text()
        self.parent_window.textlistview.view.grab_focus()

    def focus_current_view(self):
        if self.local_groups_view.has_row_selected():
            self.local_groups_view.grab_focus()
        elif self.trash_view.has_row_selected():
            self.trash_view.grab_focus()
        elif self.collection_class_selected:
            self.collection_list.grab_focus()
