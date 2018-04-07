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

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from gettext import gettext as _

from draftsrc.views.panelview import DraftTextListView, DraftLibraryView
from draftsrc.views.contentview import ContentView


class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    library_panel_hidden = False
    text_panel_hidden = False
    lock_library_panel = False
    lock_text_panel = False

    def __repr__(self):
        return '<ApplicationWindow>'

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Draft")

        self.set_default_size(800, 600)

        if Gdk.Screen.get_default().get_height() < 700:
            self.maximize()

        self.set_icon_name("draft")
        self._set_up_actions()
        self._set_up_widgets()
        self.show_all()

    def _set_up_actions(self):
        action_entries = [
            ('new_text', self._new_text_request),
            ('new_group', self._new_group_request),
            ('show_only_text_panel', self._show_only_text_panel),
            ('show_both_panels', self._show_both_panels),
            ('hide_both_panels', self._hide_both_panels)
        ]

        for action, cb in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', cb)
            self.add_action(simple_action)

    def _set_up_widgets(self):
        self._library_hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self._textlist_hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self._content_hsize_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        titlebar = _DraftHeaderBar(self,
                                   self._library_hsize_group,
                                   self._textlist_hsize_group,
                                   self._content_hsize_group)
        self.set_titlebar(titlebar)
        titlebar.connect('panels-toggled', self._on_panels_toggled)
        titlebar.connect('search-toggled', self._on_search_toggled)
        titlebar.connect('preview-toggled', self._on_preview_toggled)

        self._topbox = Gtk.Box()
        self.add(self._topbox)

        self._set_up_panel_views()
        self._set_up_content_view()
        GLib.idle_add(self.libraryview.select_appropriate_row)
        self.connect('key-press-event', self._on_key_press)

    def _set_up_panel_views(self):
        self.libraryview = DraftLibraryView(self)
        self._topbox.pack_start(self.libraryview, False, True, 0)
        self._library_hsize_group.add_widget(self.libraryview)
        self.textlistview = DraftTextListView(self)
        self._topbox.pack_start(self.textlistview, False, True, 0)
        self._textlist_hsize_group.add_widget(self.textlistview)

    def _set_up_content_view(self):
        self.contentview = ContentView(self)
        self._topbox.pack_start(self.contentview, False, True, 0)
        self._content_hsize_group.add_widget(self.contentview)
        # TODO: make this switchable, when supporting side-by-side editing
        self.textlistview.set_editor(self.contentview.content_editor)

    def _new_text_request(self, action, param):
        self.textlistview.new_text_request()

    def _new_group_request(self, action, param):
        self.libraryview.new_group_request()

    def _show_only_text_panel(self, action, param):
        if not self.library_panel_hidden:
            self.hide_library_panel()
        if self.text_panel_hidden:
            self.reveal_text_panel()

    def _show_both_panels(self, action, param):
        if self.library_panel_hidden:
            self.reveal_library_panel()
        if self.text_panel_hidden:
            self.reveal_text_panel()

    def _hide_both_panels(self, action, param):
        if not self.library_panel_hidden:
            self.hide_library_panel()
        if not self.text_panel_hidden:
            self.hide_text_panel()

    def _escape_selection_modes(self):
        self.textlistview.escape_selection_mode()
        self.libraryview.escape_selection_mode()

    def _on_panels_toggled(self, widget):
        if (not self.library_panel_hidden
                or not self.text_panel_hidden):
            self._hide_both_panels(None, None)
        else:
            self._show_both_panels(None, None)

    def _on_search_toggled(self, widget):
        self.textlistview.search_toggled()

    def _on_preview_toggled(self, widget):
        self.contentview.preview_toggled()

    def _on_key_press(self, widget, event):
        modifier = Gtk.accelerator_get_default_mod_mask()
        modifier = (event.state & modifier)

        if modifier:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK

            if (event.keyval == Gdk.KEY_F9
                    and modifier == control_mask):
                if self.library_panel_hidden:
                    self.reveal_library_panel()
                    self.reveal_text_panel()
                else:
                    self.hide_library_panel()
        else:
            if event.keyval == Gdk.KEY_F9:
                if self.text_panel_hidden:
                    self.reveal_text_panel()
                else:
                    self.hide_text_panel()
                    self.hide_library_panel()
            elif event.keyval == Gdk.KEY_Escape:
                self.textlistview.search_mode_off()
                self._escape_selection_modes()

    def hide_library_panel(self):
        if self.libraryview in self._library_hsize_group.get_widgets():
            self._library_hsize_group.remove_widget(self.libraryview)
        self.libraryview.hide_panel()
        self.library_panel_hidden = True
        if self.text_panel_hidden:
            self.panel_button_active(False)
        else:
            self.panel_button_active(True)

    def reveal_library_panel(self):
        if self.lock_library_panel:
            return
        self.libraryview.reveal_panel()
        self.library_panel_hidden = False
        self.panel_button_active(True)
        self._library_hsize_group.add_widget(self.libraryview)

    def hide_text_panel(self):
        if self.textlistview in self._textlist_hsize_group.get_widgets():
            self._textlist_hsize_group.remove_widget(self.textlistview)
        self.textlistview.hide_panel()
        self.text_panel_hidden = True
        if self.library_panel_hidden:
            self.panel_button_active(False)
        else:
            self.panel_button_active(True)

    def reveal_text_panel(self):
        if self.lock_text_panel and not self.textlistview.search_mode_is_on():
            return
        self.textlistview.reveal_panel()
        self.text_panel_hidden = False
        self.panel_button_active(True)
        self._textlist_hsize_group.add_widget(self.textlistview)

    def update_content_view_and_headerbar(self):
        if self.libraryview.collection_is_empty():
            self.contentview.set_empty_collection_state()
            self.hide_headerbar_elements()
            self.hide_library_panel()
            self.lock_text_panel = True
            self.hide_text_panel()
            self.lock_text_panel = True
        elif self.libraryview.selected_group_has_no_texts():
            if self.libraryview.selected_group_is_in_trash():
                self.new_text_button_sensitive(False)
                if self.libraryview.trash_is_empty():
                    self.contentview.set_empty_trash_state()
                elif (self.libraryview.trash_has_no_texts() and
                        self.libraryview.selected_group_is_top_level()):
                    self.contentview.set_empty_trash_texts_state()
                else:
                    self.contentview.set_empty_trashed_group_state()
            else:
                self.new_text_button_sensitive(True)
                self.contentview.set_empty_group_state()

            if self.textlistview.search_mode_is_on():
                self.textlistview.search_mode_off()
            self.show_headerbar_elements()
            self.partial_headerbar_interaction()
            self.lock_library_panel = False
            self.hide_text_panel()
            self.lock_text_panel = True
        else:
            if self.libraryview.selected_group_is_in_trash():
                self.new_text_button_sensitive(False)
            else:
                self.new_text_button_sensitive(True)

            self.contentview.set_last_content_state()
            self.show_headerbar_elements()
            self.complete_headerbar_interaction()
            self.lock_library_panel = False
            self.lock_text_panel = False
            self.reveal_text_panel()

    def hide_headerbar_elements(self):
        headerbar = self.get_titlebar()
        headerbar.set_elements_visible(False)

    def show_headerbar_elements(self):
        headerbar = self.get_titlebar()
        headerbar.set_elements_visible(True)

    def partial_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_sensitive(False)

    def complete_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_sensitive(True)

    def search_button_active(self, active):
        headerbar = self.get_titlebar()
        headerbar.set_search_button_active(active)

    def new_text_button_sensitive(self, sensitive):
        headerbar = self.get_titlebar()
        headerbar.set_new_button_sensitive(sensitive)

    def panel_button_active(self, active):
        headerbar = self.get_titlebar()
        headerbar.set_panel_button_active(active)

    def create_new_dialog_box(self):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Draft/dialogbox.ui')
        dialog_box = builder.get_object('dialog_box')
        dialog_box.set_transient_for(self)
        return dialog_box

    def bring_up_final_deletion_dialog(self, delete_texts=False, num_items=1):
        dialog_box = self.create_new_dialog_box()
        if delete_texts:
            head = _("Are you sure you want to delete the %s selected items?") % num_items
            info = _("If you delete the items, they will be permanently lost.")
            if num_items == 1:
                head = _("Are you sure you want to delete the selected text?")
                info = _("If you delete this text, it will be permanently lost.")
            markup = '<big><b>%s</b></big>' % head
            dialog_box.set_markup(markup)
            dialog_box.format_secondary_text(info)
        else:
            head = _("Are you sure you want to delete the selected group?")
            info = _("If you delete this group, all subgroups and texts contained within will be permanently deleted along with it.")
            markup = '<big><b>%s</b></big>' % head
            dialog_box.set_markup(markup)
            dialog_box.format_secondary_text(info)
        dialog_box.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog_box.add_button(_("Delete"), Gtk.ResponseType.ACCEPT)
        del_button = dialog_box.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        ctx = del_button.get_style_context()
        ctx.add_class('destructive-action')
        dialog_box.set_default_response(Gtk.ResponseType.ACCEPT)
        return dialog_box

    def bring_up_orphan_restore_dialog(self, restore_texts=False, num_items=1):
        dialog_box = self.create_new_dialog_box()
        if restore_texts:
            head = _("Are you sure you want to restore these texts?")
            info = _("If you restore these texts without their parent_group, they will be orphaned and appear in “Local” texts.")
            if num_items == 1:
                head = _("Are you sure you want to restore this text?")
                info = _("If you restore this text without its parent group, it will be orphaned and appear in “Local” texts.")
            markup = '<big><b>%s</b></big>' % head
            dialog_box.set_markup(markup)
            dialog_box.format_secondary_text(info)
        else:
            head = _("Are you sure you want to restore the selected group?")
            info = _("If you restore this group without its parent, it will become a top level group within “Local” groups.")
            markup = '<big><b>%s</b></big>' % head
            dialog_box.set_markup(markup)
            dialog_box.format_secondary_text(info)
        dialog_box.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog_box.add_button(_("Restore"), Gtk.ResponseType.ACCEPT)
        dialog_box.set_default_response(Gtk.ResponseType.ACCEPT)
        return dialog_box


class _DraftHeaderBar(Gtk.Box):
    __gtype_name__ = 'DraftHeaderBar'

    __gsignals__ = {
        'panels-toggled': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'search-toggled': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'preview-toggled': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<DraftHeaderBar>'

    def __init__(self, parent, library_hsize_group, list_hsize_group, content_hsize_group):
        Gtk.Box.__init__(self)
        self.parent = parent
        self._set_up_widgets(library_hsize_group, list_hsize_group, content_hsize_group)

    def _set_up_widgets(self, library_hsize_group, list_hsize_group, content_hsize_group):
        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/org/gnome/Draft/headerbar.ui')

        self._library_header = self._builder.get_object('library_header')
        self.pack_start(self._library_header, False, False, 0)
        library_hsize_group.add_widget(self._library_header)

        self._list_header = self._builder.get_object('list_header')
        self.pack_start(self._list_header, False, False, 0)
        list_hsize_group.add_widget(self._list_header)

        self._content_header = self._builder.get_object('content_header')
        self.pack_start(self._content_header, True, True, 0)
        content_hsize_group.add_widget(self._content_header)

        self._update_decorations(Gtk.Settings.get_default(), None)

        self._toggle_panel_button = self._builder.get_object('toggle_panel_button')
        self._toggle_handler_id = self._toggle_panel_button.connect('clicked',
                                                                    self._on_toggle_panel_clicked)
        self._toggle_popup_button = self._builder.get_object('toggle_popup_button')
        self._toggle_popup_button.connect('toggled', self._on_toggle_popup_clicked)

        self._toggle_popup_menu = self._builder.get_object('toggle_panel_popup')
        self._toggle_popup_menu.connect('closed', self._on_toggle_popup_closed)

        self._text_only_button = self._builder.get_object('texts_only_button')
        self._show_both_button = self._builder.get_object('show_both_button')
        self._hide_both_button = self._builder.get_object('hide_both_button')

        self._search_button = self._builder.get_object('search_button')
        self._search_button.connect('toggled', self._on_search_toggled)
        self._preview_button = self._builder.get_object('preview_button')
        self._preview_button.connect('toggled', self._on_preview_toggled)
        self._new_button = self._builder.get_object('new_button')

    def _on_toggle_panel_clicked(self, widget):
        self.emit('panels-toggled')

    def _on_toggle_popup_clicked(self, widget):
        if not self._toggle_popup_button.get_active():
            return

        # Maybe too much hardcoded logic in here. A cleaner way?
        if self.parent.text_panel_hidden and self.parent.library_panel_hidden:
            self._text_only_button.set_visible(True)
            self._hide_both_button.set_visible(False)
            self._show_both_button.set_visible(True)
        elif not self.parent.text_panel_hidden and not self.parent.library_panel_hidden:
            self._text_only_button.set_visible(True)
            self._hide_both_button.set_visible(True)
            self._show_both_button.set_visible(False)
        elif not self.parent.text_panel_hidden and self.parent.library_panel_hidden:
            self._text_only_button.set_visible(False)
            self._hide_both_button.set_visible(True)
            self._show_both_button.set_visible(True)
        else:
            self._text_only_button.set_visible(True)
            self._hide_both_button.set_visible(True)
            self._show_both_button.set_visible(True)

        visibility = self._show_both_button.get_visible()
        if self.parent.lock_text_panel:
            self._text_only_button.set_sensitive(False)
            if not self.parent.library_panel_hidden:
                self._show_both_button.set_visible(False)
        else:
            self._text_only_button.set_sensitive(True)
            self._show_both_button.set_visible(visibility)

        self._toggle_popup_menu.popup()

    def _on_toggle_popup_closed(self, widget):
        self._toggle_popup_button.set_active(False)

    def _on_search_toggled(self, widget):
        self.emit('search-toggled')

    def _on_preview_toggled(self, widget):
        self.emit('preview-toggled')

    def set_elements_visible(self, visible):
        self._toggle_panel_button.set_visible(visible)
        self._toggle_popup_button.set_visible(visible)
        self._new_button.set_visible(visible)
        self._search_button.set_visible(visible)
        self._preview_button.set_visible(visible)

    def set_preview_button_sensitive(self, sensitive):
        self._preview_button.set_sensitive(sensitive)

    def set_search_button_active(self, active):
        self._search_button.set_active(active)

    def set_new_button_sensitive(self, sensitive):
        self._new_button.set_sensitive(sensitive)

    def set_panel_button_active(self, active):
        with self._toggle_panel_button.handler_block(self._toggle_handler_id):
            self._toggle_panel_button.set_active(active)

    def _update_decorations(self, settings, pspec):
        layout_desc = settings.props.gtk_decoration_layout;
        tokens = layout_desc.split(":", 1)
        if len(tokens) > 1:
            self._content_header.props.decoration_layout = ":" + tokens[1]
        else:
            self._right_header.props.decoration_layout = ""
        self._library_header.props.decoration_layout = tokens[0]
