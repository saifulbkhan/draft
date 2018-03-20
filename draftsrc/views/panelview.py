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

from gi.repository import Gtk, GLib, Pango, Gdk, GObject

from draftsrc.widgets.grouptree import DraftGroupTree
from draftsrc.widgets.textlist import DraftTextList


class DraftCollectionView(Gtk.Bin):
    """A container bounding a GtkTreeView that allows for slider based hiding
    and resizing"""
    _panel_visible = True
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
        self.view = DraftGroupTree()
        scrolled.add(self.view)

        self._popover = self.builder.get_object('popover')
        self._popover_title = self.builder.get_object('popover_title')
        self._name_entry = self.builder.get_object('text_entry')
        self._action_button = self.builder.get_object('action_button')

        self._popover_menu = self.builder.get_object('popover_menu')
        self._rename_button = self.builder.get_object('rename_button')
        self._delete_button = self.builder.get_object('delete_button')

        self.view.connect('group-selected', self._on_group_selected)
        self.view.connect('texts-dropped', self._on_texts_dropped)
        self.view.connect('rename-requested', self._on_group_rename_requested)
        self.view.connect('menu-requested', self._on_group_menu_requested)
        self.view.connect('group-created', self._on_group_created)
        self.view.connect('group-deleted', self._on_group_deleted)

        self._action_button.connect('clicked', self._on_name_set)
        self._name_entry.connect('activate', self._on_name_set)
        self._name_entry.connect('changed', self._on_name_entry_changed)
        self._popover.connect('closed', self._on_popover_closed)
        self._rename_button.connect('clicked', self._on_rename_clicked)
        self._delete_button.connect('clicked', self._on_delete_clicked)

    def _on_group_selected(self, widget, group):
        """Handler for `group-selected` signal from DraftsTreeView. Calls on
        TextListView to reload its model with texts from selected group"""
        self.parent_window.update_content_view_and_headerbar()
        self.parent_window.textlistview.set_model_for_group(group)

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

    def _on_group_rename_requested(self, widget):
        """Handle request for group rename, set button and popover title"""
        rect = self.view.get_selected_rect()
        self._action_button.set_label('Rename')
        self._popover_title.set_label('Rename Group')
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _on_group_created(self, widget):
        """Handle view's `group-created` signal"""
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_deleted(self, widget):
        """Handle view's `group-deleted` signal"""
        self.parent_window.update_content_view_and_headerbar()

    def _on_group_menu_requested(self, widget):
        """Cater to context menu request for a group. Ignore if the selection
        is the root container."""

        def popup_menu():
            if self.view.get_selected_path().to_string() == '0':
                return

            rect = self.view.get_selected_rect()
            self._popover_menu.set_pointing_to(rect)
            self._popover_menu.popup()

        # have to queue this in main loop, so that correct GdkRectangle is
        # selected before making menu point to it.
        GLib.idle_add(popup_menu)

    def _on_rename_clicked(self, widget):
        self.view.emit('rename-requested')
        self._popover_menu.popdown()

    def _on_delete_clicked(self, widget):
        self.view.delete_selected_row()
        self._popover_menu.popdown()

    def toggle_panel(self):
        """Toggle the reveal status of slider's child"""
        if self._panel_visible:
            self.hide_panel()
        else:
            self.reveal_panel()

    def hide_panel(self):
        """Hide the slider's child"""
        self.slider.set_reveal_child(False)
        self._panel_visible = False

    def reveal_panel(self):
        """Reveal the slider's child"""
        self.slider.set_reveal_child(True)
        self._panel_visible = True

    def new_group_request(self):
        """Cater to the request for new group creation. Pops up an entry to set
        the name of the new group as well"""
        self.reveal_panel()

        rect = self.view.new_group_request()
        self.view.set_faded_selection(True)

        self._creation_state = True
        self._action_button.set_label('Create')
        self._popover_title.set_label('Group Name')
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def selection_request(self, group_id):
        self.view.select_for_id(group_id)

    def escape_selection_mode(self):
        pass

    def collection_is_empty(self):
        """Check if there are any groups or texts present in the collection"""
        num_groups, num_texts = self.view.count_top_level_groups_and_texts()
        if num_groups or num_texts:
            return False

        return True

    def selected_group_has_no_texts(self):
        """Check if selected group has any texts"""
        num_groups, num_texts = self.view.count_groups_and_texts_for_selection()
        if num_texts:
            return False

        return True


# TODO: Make this a stack for storing multiple DraftTextsList
class DraftTextListView(Gtk.Bin):

    _panel_visible = True
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
        self.view = DraftTextList()
        listview.add(self.view)

        self.search_bar = self.builder.get_object('search_bar')
        self.search_entry = self.builder.get_object('search_entry')

        self.view.connect('text-moved-to-group', self._on_text_moved_to_group)
        self.view.connect('text-deleted', self._on_text_deleted)
        self.view.connect('text-created', self._on_text_created)

    def toggle_panel(self):
        if self._panel_visible:
            self.hide_panel()
        else:
            self.reveal_panel()

    def hide_panel(self):
        """Hide the slider's child"""
        self.slider.set_reveal_child(False)
        self._panel_visible = False

    def reveal_panel(self):
        """Reveal the slider's child"""
        self.slider.set_reveal_child(True)
        self._panel_visible = True

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

    def set_group_for_texts(self, text_ids, group_id):
        self.view.set_group_for_ids(text_ids, group_id)

    def escape_selection_mode(self):
        if self.view.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self.view.set_multi_selection_mode(False, escape=True)

    def _on_text_moved_to_group(self, widget, group_id):
        self.parent_window.grouptreeview.selection_request(group_id)

    def _on_text_deleted(self, widget):
        self.parent_window.update_content_view_and_headerbar()

    def _on_text_created(self, widget):
        self.parent_window.update_content_view_and_headerbar()
