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

from gettext import gettext as _

from gi.repository import Gtk, GLib, Gdk

from draftsrc import search
from draftsrc.widgetmodels.collectionliststore import CollectionClassType
from draftsrc.widgets.textlist import DraftTextList, DraftResultList


class DraftTextListView(Gtk.Bin):
    panel_visible = True
    _group_shown = None
    _last_search_terms = ""
    sidebar_width = 250

    def __repr__(self):
        return '<TextListView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Draft/textpanelview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.slider = self.builder.get_object('slider')
        self.slider.set_hexpand(False)
        self.textstack = self.builder.get_object('textstack')
        self.listview = self.builder.get_object('listview')
        self.resultview = self.builder.get_object('resultview')
        self.empty_label = self.builder.get_object('empty_label')

        self.add(self.slider)
        self.view = DraftTextList()
        self.listview.add(self.view)
        self.resultlistview = DraftResultList()
        self.resultview.add(self.resultlistview)

        self.search_bar = self.builder.get_object('search_bar')
        self.search_entry = self.builder.get_object('search_entry')
        self.search_bar.connect_entry(self.search_entry)
        self._search_menu = self.builder.get_object('search_menu')
        self._search_options_button = self.builder.get_object('search_options_button')
        self._search_content_button = self.builder.get_object('search_content')
        self._search_tags_button = self.builder.get_object('search_tags')
        self._title_label = self.builder.get_object('title_label')

        self._text_menu = self.builder.get_object('text_menu')
        self._open_button = self.builder.get_object('open_button')
        self._trash_button = self.builder.get_object('trash_button')

        self._trash_menu = self.builder.get_object('trash_menu')
        self._restore_button = self.builder.get_object('restore_button')
        self._delete_button = self.builder.get_object('delete_button')

        self.view.connect('text-moved-to-group', self._on_text_moved_to_group)
        self.view.connect('text-deleted', self._on_text_deleted)
        self.view.connect('text-created', self._on_text_created)
        self.view.connect('text-restored', self._on_text_restored)
        self.view.connect('text-title-changed', self._on_text_title_changed)
        self.view.connect('menu-requested', self._on_menu_requested)
        self.view.connect('selection-requested', self._on_selection_requested)
        self.view.connect('no-text-selected', self._on_no_text_selected)
        self.view.connect('some-text-selected', self._on_some_text_selected)
        self.view.connect('key-press-event', self._on_view_key_press)
        self.view.connect('reveal-requested', self._on_reveal_requested)
        self.resultlistview.connect('reveal-requested', self._on_reveal_requested)

        self.search_entry.connect('search-changed', self._on_search_changed)
        self._search_menu.connect('closed', self._on_search_menu_closed)
        self._search_options_button.connect('toggled', self._on_search_options_toggled)
        self._search_content_button.connect('toggled', self._on_search_content_toggled)
        self._search_tags_button.connect('toggled', self._on_search_tags_toggled)
        self._open_button.connect('clicked', self._on_open_clicked)
        self._trash_button.connect('clicked', self._on_trash_clicked)
        self._restore_button.connect('clicked', self._on_restore_clicked)
        self._delete_button.connect('clicked', self._on_delete_clicked)

    def toggle_panel(self):
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

    def search_toggled(self):
        if self.search_mode_is_on():
            self.search_mode_off()
            self.parent_window.update_content_view_and_headerbar()
        else:
            self.search_mode_on()
            self.parent_window.reveal_text_panel()

    def search_mode_is_on(self):
        return self.search_bar.get_search_mode()

    def search_mode_on(self):
        self.parent_window.search_button_active(True)
        self.search_bar.set_search_mode(True)
        self.search_entry.set_text(self._last_search_terms)
        self.search_entry.grab_focus()

    def search_mode_off(self):
        search_terms = self.search_entry.get_text()
        self._last_search_terms = search_terms
        self.textstack.set_visible_child(self.listview)
        self.parent_window.search_button_active(False)
        self.search_bar.set_search_mode(False)

    def set_model_for_group(self, group):
        self._group_shown = group
        self._title_label.set_label(group.get('name'))
        self.view.set_model(parent_group=group)
        if not self.view.text_view_selection_in_progress:
            self.search_mode_off()

    def set_collection_class_type(self, collection_class_type):
        self._group_shown = None
        if collection_class_type == CollectionClassType.ALL:
            self._title_label.set_label(_("All Texts"))
        elif collection_class_type == CollectionClassType.RECENT:
            self._title_label.set_label(_("Recently Edited Texts"))
        self.view.set_model(collection_class_type)

    def set_editor(self, editor):
        self.view.editor = editor
        self.resultlistview.editor = editor

    def new_text_request(self):
        if not self._group_shown or self._group_shown['in_trash']:
            return

        self.view.new_text_request()
        if self.search_mode_is_on():
            self.search_mode_off()

    def set_group_for_texts(self, text_ids, group_id):
        self.view.set_group_for_ids(text_ids, group_id)

    def escape_selection_mode(self):
        if self.view.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self.view.set_multi_selection_mode(False)

    def delete_all_texts_permanently(self):
        # warning: assuming the user has been already informed by library view.
        self.view.delete_all_rows_permanently()

    def get_num_items(self):
        return self.view.get_num_items()

    def _on_text_moved_to_group(self, widget, group_id):
        self.parent_window.libraryview.selection_request(group_id)

    def _on_text_deleted(self, widget, permanent):
        self.parent_window.update_content_view_and_headerbar()

    def _on_text_created(self, widget):
        self.parent_window.update_content_view_and_headerbar()

    def _on_text_restored(self, widget):
        self.parent_window.update_content_view_and_headerbar()

    def _on_text_title_changed(self, widget, title, subtitle, update_sub):
        self.parent_window.set_content_title(title, subtitle, update_sub)

    def _on_no_text_selected(self, widget):
        self.parent_window.set_empty_selection_state(True)

    def _on_some_text_selected(self, widget):
        self.parent_window.set_empty_selection_state(False)

    def _on_menu_requested(self, widget, rect, in_trash):

        def popup_menu():
            if in_trash:
                self._trash_menu.set_relative_to(self.view)
                self._trash_menu.set_pointing_to(rect)
                self._trash_menu.popup()
            else:
                if self.view.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
                    self._open_button.set_sensitive(False)
                else:
                    self._open_button.set_sensitive(True)

                self._text_menu.set_relative_to(self.view)
                self._text_menu.set_pointing_to(rect)
                self._text_menu.popup()

        # have to queue this in main loop, so that correct GdkRectangle is
        # selected before making menu point to it.
        GLib.idle_add(popup_menu)

    def _on_selection_requested(self, widget, group_id, text_id, in_trash):
        self.parent_window.libraryview.selection_request(group_id, in_trash)
        self.view.select_for_id(text_id)

    def _on_open_clicked(self, widget):
        self.view.activate_selected_row()

    def _on_trash_clicked(self, widget):
        self.view.delete_selected()

    def _on_restore_clicked(self, widget):
        num_rows = self.view.selected_rows_will_be_orphaned()
        if num_rows:
            dialog = self.parent_window.bring_up_orphan_restore_dialog(restore_texts=True,
                                                                       num_items=num_rows)
            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                self.view.restore_selected()
            dialog.destroy()
        else:
            self.view.restore_selected()

    def _on_delete_clicked(self, widget):
        num_rows = len(self.view.get_selected_rows())
        dialog = self.parent_window.bring_up_final_deletion_dialog(delete_texts=True,
                                                                   num_items=num_rows)
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.view.delete_selected(permanent=True)
        dialog.destroy()

    def _on_search_options_toggled(self, widget):
        if widget.get_active():
            self._search_menu.popup()
        else:
            self._search_menu.popdown()

    def _on_search_menu_closed(self, widget):
        self._search_options_button.set_active(False)

    def _on_search_content_toggled(self, widget):
        if self._search_content_button.get_active():
            self._on_search_changed(self.search_entry)

    def _on_search_tags_toggled(self, widget):
        if self._search_tags_button.get_active():
            self._on_search_changed(self.search_entry)

    def _on_search_changed(self, search_entry):
        search_terms = search_entry.get_text()
        search_terms = search_terms.strip()
        if not search_terms:
            self.textstack.set_visible_child(self.listview)
            return

        search_tags = self._search_tags_button.get_active()

        group_id = None
        in_trash = False
        if self._group_shown is not None:
            group_id = self._group_shown['id']
            in_trash = self._group_shown['in_trash']

        def post_search_callback(results):
            if not len(results) > 0:
                self.textstack.set_visible_child(self.empty_label)
                return
            else:
                self.textstack.set_visible_child(self.resultview)
            self.resultlistview.set_model(results, search_tags, in_trash)

        search.text_finder.search_in_group_threaded(group_id,
                                                    search_terms,
                                                    search_tags,
                                                    in_trash,
                                                    post_search_callback)

    def _on_view_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if event_and_modifiers:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            if (event.keyval == Gdk.KEY_f
                    and event_and_modifiers == control_mask):
                self.search_mode_on()
            if (event.keyval == Gdk.KEY_n
                    and event_and_modifiers == control_mask):
                self.new_text_request()
        else:
            if (event.keyval == Gdk.KEY_Left
                    and self.parent_window.libraryview.panel_visible):
                self.parent_window.libraryview.focus_current_view()

    def _on_reveal_requested(self, widget):
        self.reveal_panel()
