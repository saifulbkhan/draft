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
from gi.repository import Gtk, Gdk, Gio, GLib

from draftsrc.widgets.headerbar import DraftHeaderBar
from draftsrc.views.librarypanelview import DraftLibraryView
from draftsrc.views.textpanelview import DraftTextListView
from draftsrc.views.contentview import ContentView
from draftsrc.widgetmodels.collectionliststore import CollectionClassType
from draftsrc import export


class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    library_panel_hidden = False
    text_panel_hidden = False
    lock_library_panel = False
    lock_text_panel = False
    in_fullscreen_mode = False

    def __repr__(self):
        return '<ApplicationWindow>'

    def __init__(self, app, settings):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Draft")
        self.app_settings = settings

        self.set_default_size(800, 600)

        if Gdk.Screen.get_default().get_height() < 700:
            self.maximize()

        self.set_icon_name("draft")
        self._set_up_actions()
        self._set_up_widgets()
        self.show_all()
        self._set_up_for_app_settings()
        export.main_window = self

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
        titlebar = DraftHeaderBar(self,
                                  self._library_hsize_group,
                                  self._textlist_hsize_group,
                                  self._content_hsize_group)
        self.set_titlebar(titlebar)
        titlebar.connect('panels-toggled', self._on_panels_toggled)
        titlebar.connect('search-toggled', self._on_search_toggled)
        titlebar.connect('preview-toggled', self._on_preview_toggled)
        titlebar.connect('export-requested', self._on_export_requested)

        self._header_revealer = Gtk.Revealer()
        self._header_revealer.set_valign(Gtk.Align.START)
        self._header_revealer.set_vexpand(False)

        self._topbox = Gtk.Box()
        self._overlay = Gtk.Overlay()
        self._overlay.add(self._topbox)
        self._overlay.add_overlay(self._header_revealer)
        self.add(self._overlay)

        self._set_up_panel_views()
        self._set_up_content_view()
        GLib.idle_add(self.libraryview.select_appropriate_row)
        self.connect('key-press-event', self._on_key_press)
        self.connect('motion-notify-event', self._on_motion_event)

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
        headerbar = self.get_titlebar()
        headerbar.set_editor(self.contentview.content_editor)

    def _set_up_for_app_settings(self):
        library_panel_visible = self.app_settings.get_value('library-panel-visible')
        if library_panel_visible:
            self.reveal_library_panel()
        else:
            self.hide_library_panel()

        self._update_dark_theme()
        self.app_settings.connect('changed', self._on_settings_changed)

    def _update_dark_theme(self):
        settings = Gtk.Settings.get_default()
        gtk_dark = settings.get_property('gtk-application-prefer-dark-theme')
        app_dark = self.app_settings.get_value('dark-ui')
        if not gtk_dark == app_dark:
            settings.set_property('gtk-application-prefer-dark-theme', app_dark)

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

    def _on_settings_changed(self, settings, key):
        if key == 'dark-ui':
            self._update_dark_theme()
        elif key == 'color-scheme':
            self.contentview.content_editor.update_style_scheme_for_settings()
        elif key == 'stylesheet':
            self.contentview.content_preview.update_stylesheet_for_settings()
        elif key == 'editor-font':
            self.contentview.content_editor.update_font_for_settings()
        elif key == 'typewriter-mode':
            self.contentview.content_editor.update_typewriter_mode_for_settings()

    def _on_panels_toggled(self, widget):
        self.toggle_panels()

    def _on_search_toggled(self, widget):
        self.textlistview.search_toggled()

    def _on_preview_toggled(self, widget):
        self.contentview.preview_toggled()

    def _on_export_requested(self, widget):
        self.contentview.html_export_requested()

    def _on_key_press(self, widget, event):
        modifier = Gtk.accelerator_get_default_mod_mask()
        modifier = (event.state & modifier)

        if modifier:
            control_mask = Gdk.ModifierType.CONTROL_MASK
            shift_mask = Gdk.ModifierType.SHIFT_MASK
            headerbar = self.get_titlebar()

            if (event.keyval == Gdk.KEY_F9
                    and modifier == control_mask):
                if self.library_panel_hidden:
                    self.reveal_library_panel()
                    self.reveal_text_panel()
                else:
                    self.hide_library_panel()
            elif (event.keyval == Gdk.KEY_p
                    and modifier == control_mask):
                if headerbar.has_preview_available():
                    headerbar.activate_preview()
            elif (event.keyval == Gdk.KEY_m
                    and modifier == control_mask):
                headerbar.activate_markup_reference()
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
            elif event.keyval == Gdk.KEY_F11:
                if self.in_fullscreen_mode:
                    self.go_unfullscreen()
                else:
                    self.go_fullscreen()

    def _on_motion_event(self, widget, event):
        if event.y_root <= 1 and self.in_fullscreen_mode:
            self._header_revealer.set_reveal_child(True)
        elif (event.y_root >= self.get_titlebar().get_allocated_height()
                and self.in_fullscreen_mode
                and not self.get_titlebar().popup_active):
            self._header_revealer.set_reveal_child(False)

    def get_titlebar(self):
        if self.in_fullscreen_mode:
            return self._header_revealer.get_child()
        return Gtk.Window.get_titlebar(self)

    def go_fullscreen(self):
        self.fullscreen()
        self._hide_both_panels(None, None)
        self.contentview.content_editor.fullscreen_mode()
        headerbar = self.get_titlebar()
        temp_header = Gtk.HeaderBar()
        self.set_titlebar(temp_header)
        headerbar.set_fullscreen_mode(True)
        self._header_revealer.add(headerbar)
        self.in_fullscreen_mode = True

    def go_unfullscreen(self):
        headerbar = self._header_revealer.get_child()
        self._header_revealer.set_reveal_child(False)
        self._header_revealer.remove(headerbar)
        headerbar.set_fullscreen_mode(False)
        self.set_titlebar(headerbar)
        self.contentview.content_editor.regular_mode()
        self.unfullscreen()
        self.in_fullscreen_mode = False

    def toggle_panels(self):
        if (not self.library_panel_hidden
                or not self.text_panel_hidden):
            self._hide_both_panels(None, None)
        else:
            self._show_both_panels(None, None)

    def hide_library_panel(self):
        if self.libraryview in self._library_hsize_group.get_widgets():
            self._library_hsize_group.remove_widget(self.libraryview)
        self.libraryview.hide_panel()
        self.library_panel_hidden = True
        self.show_library_header(False)
        if self.text_panel_hidden:
            self.panel_button_active(False)
        else:
            self.panel_button_active(True)
        self.app_settings.set_value('library-panel-visible',
                                    GLib.Variant('b', False))

    def reveal_library_panel(self):
        if self.lock_library_panel:
            return
        self.library_panel_hidden = False
        self.libraryview.reveal_panel()
        self.panel_button_active(True)
        self.show_library_header(True)
        self._library_hsize_group.add_widget(self.libraryview)
        self.app_settings.set_value('library-panel-visible',
                                    GLib.Variant('b', True))

    def hide_text_panel(self):
        if self.textlistview in self._textlist_hsize_group.get_widgets():
            self._textlist_hsize_group.remove_widget(self.textlistview)
        self.textlistview.hide_panel()
        self.text_panel_hidden = True
        self.show_textlist_header(False)
        if self.library_panel_hidden:
            self.panel_button_active(False)
        else:
            self.panel_button_active(True)

    def reveal_text_panel(self):
        if self.lock_text_panel and not self.textlistview.search_mode_is_on():
            return
        self.text_panel_hidden = False
        self.textlistview.reveal_panel()
        self.panel_button_active(True)
        self.show_textlist_header(True)
        self._textlist_hsize_group.add_widget(self.textlistview)

    def set_empty_selection_state(self, empty_selection):
        if empty_selection:
            self.contentview.set_empty_selection_state()
            self.partial_headerbar_interaction()
            self.set_content_title("", update_sub=True)
        else:
            self.update_content_view_and_headerbar()

    def update_content_view_and_headerbar(self):
        if self.libraryview.collection_is_empty():
            self.contentview.set_empty_collection_state()
            self.set_content_title("")
            self.hide_headerbar_elements()
            self.hide_library_panel()
            self.lock_library_panel = True
            self.hide_text_panel()
            self.lock_text_panel = True
        elif self.libraryview.collection_class_selected:
            if (self.libraryview.collection_class_selected == CollectionClassType.RECENT
                    and self.textlistview.get_num_items() == 0):
                self.set_content_title("")
                self.contentview.set_empty_recent_state()
                self.show_headerbar_elements(disallow_creation=True)
                self.partial_headerbar_interaction()
                self.hide_text_panel()
                self.lock_text_panel = True
            else:
                self.show_headerbar_elements(disallow_creation=True)
                self.complete_headerbar_interaction()
                self.lock_text_panel = False
                self.reveal_text_panel()
                self.contentview.set_last_content_state()
        elif self.libraryview.selected_group_has_no_texts():
            if self.libraryview.selected_group_is_in_trash():
                self.show_headerbar_elements(disallow_creation=True)
                if self.libraryview.trash_is_empty():
                    self.contentview.set_empty_trash_state()
                elif (self.libraryview.trash_has_no_texts() and
                        self.libraryview.selected_group_is_top_level()):
                    self.contentview.set_empty_trash_texts_state()
                else:
                    self.contentview.set_empty_trashed_group_state()
            else:
                self.show_headerbar_elements()
                self.contentview.set_empty_group_state()

            if self.textlistview.search_mode_is_on():
                self.textlistview.search_mode_off()
            self.set_content_title("", update_sub=True)
            self.partial_headerbar_interaction()
            self.lock_library_panel = False
            self.hide_text_panel()
            self.lock_text_panel = True
        else:
            if self.libraryview.selected_group_is_in_trash():
                self.show_headerbar_elements(disallow_creation=True)
                self.partial_headerbar_interaction()
            else:
                self.show_headerbar_elements()
                self.complete_headerbar_interaction()

            self.contentview.set_last_content_state()
            self.lock_library_panel = False
            self.lock_text_panel = False
            self.reveal_text_panel()

    def hide_headerbar_elements(self):
        headerbar = self.get_titlebar()
        headerbar.set_elements_visible(False)

    def show_headerbar_elements(self, disallow_creation=False):
        headerbar = self.get_titlebar()
        new_text_button_visible = not disallow_creation
        headerbar.set_elements_visible(True, new_text_button_visible)

    def partial_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_visible(False)
        headerbar.set_utility_buttons_visible(False)

    def complete_headerbar_interaction(self):
        headerbar = self.get_titlebar()
        headerbar.set_preview_button_visible(True)
        headerbar.set_utility_buttons_visible(True)

    def search_button_active(self, active):
        headerbar = self.get_titlebar()
        headerbar.set_search_button_active(active)

    def panel_button_active(self, active):
        headerbar = self.get_titlebar()
        headerbar.set_panel_button_active(active)

    def set_content_title(self, title, subtitle="", update_sub=False):
        headerbar = self.get_titlebar()
        headerbar.set_content_header_title(title)
        if update_sub:
            headerbar.set_content_header_subtitle(subtitle)

    def show_library_header(self, show):
        headerbar = self.get_titlebar()
        headerbar.set_library_header_visible(show)

    def show_textlist_header(self, show):
        headerbar = self.get_titlebar()
        headerbar.set_textlist_header_visible(show)

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

    def bring_up_emptying_trash_dialog(self):
        dialog_box = self.create_new_dialog_box()
        head = _("Empty all items from Trash?")
        info = _("All items from Trash will be permanently deleted.")
        markup = '<big><b>%s</b></big>' % head
        dialog_box.set_markup(markup)
        dialog_box.format_secondary_text(info)
        dialog_box.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog_box.add_button(_("Empty"), Gtk.ResponseType.ACCEPT)
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

    def handle_key_press(self, eventkey):
        self._on_key_press(self, eventkey)
