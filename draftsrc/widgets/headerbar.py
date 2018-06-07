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
from gi.repository import Gtk, GObject

class DraftHeaderBar(Gtk.Box):
    __gtype_name__ = 'DraftHeaderBar'

    __gsignals__ = {
        'panels-toggled': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'search-toggled': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'preview-toggled': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'export-requested': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    popup_active = False
    _editor = None
    _last_focused_widget = None
    _current_utility_buttons = []
    _passive_utility_buttons = []

    def __repr__(self):
        return '<DraftHeaderBar>'

    def __init__(self, parent, library_hsize_group, list_hsize_group, content_hsize_group):
        Gtk.Box.__init__(self)
        self.parent = parent
        self._set_up_widgets(library_hsize_group, list_hsize_group, content_hsize_group)
        self._current_utility_buttons = [self._markup_button]
        self._passive_utility_buttons = [self._export_button]

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

        self._update_decorations()

        self._toggle_panel_button = self._builder.get_object('toggle_panel_button')
        self._toggle_handler_id = self._toggle_panel_button.connect('clicked',
                                                                    self._on_toggle_panel_clicked)
        self._toggle_popup_button = self._builder.get_object('toggle_popup_button')
        self._toggle_popup_button.connect('toggled', self._on_toggle_popup_clicked)

        self._toggle_popup_menu = self._builder.get_object('toggle_panel_popup')
        self._toggle_popup_menu.connect('closed', self._on_toggle_popup_closed)

        self._cheatsheet_popover = self._builder.get_object('cheatsheet_popover')
        self._cheatsheet_popover.connect('closed', self._on_cheatsheet_popover_closed)

        self._text_only_button = self._builder.get_object('texts_only_button')
        self._show_both_button = self._builder.get_object('show_both_button')
        self._hide_both_button = self._builder.get_object('hide_both_button')

        self._search_button = self._builder.get_object('search_button')
        self._search_button.connect('toggled', self._on_search_toggled)
        self._preview_button = self._builder.get_object('preview_button')
        self._preview_button.connect('toggled', self._on_preview_toggled)
        self._preview_button.set_can_focus(False)

        self._new_button = self._builder.get_object('new_button')
        self._content_title_label = self._builder.get_object('content_title_label')
        self._content_subtitle_label = self._builder.get_object('content_subtitle_label')
        self._markup_button = self._builder.get_object('markup_button')
        self._markup_button.connect('clicked', self._on_request_markup_cheatsheet)
        self._export_button = self._builder.get_object('export_button')
        self._export_button.connect('clicked', self._on_export_clicked)

        self._library_buttons = self._builder.get_object('library_buttons')
        self._content_button_box = self._builder.get_object('content_button_box')
        self._list_button_box = self._builder.get_object('list_button_box')

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
        self.popup_active = True

    def _on_toggle_popup_closed(self, widget):
        self._toggle_popup_button.set_active(False)
        self.popup_active = False

    def _on_search_toggled(self, widget):
        self.emit('search-toggled')

    def _on_preview_toggled(self, widget):
        if widget.get_active():
            self._last_focused_widget = self._editor.get_focus_child()
            self._current_utility_buttons = [self._export_button]
            self._passive_utility_buttons = [self._markup_button]
        else:
            self._current_utility_buttons = [self._markup_button]
            self._passive_utility_buttons = [self._export_button]
        self.emit('preview-toggled')
        self.set_utility_buttons_visible(True)
        if self._last_focused_widget is not None:
            self._editor.view.grab_focus()

    def _on_export_clicked(self, widget):
        self.emit('export-requested')

    def _on_request_markup_cheatsheet(self, widget):
        self._cheatsheet_popover.popup()
        self.popup_active = True

    def _on_cheatsheet_popover_closed(self, widget):
        self._markup_button.set_active(False)
        self.popup_active = False

    def set_elements_visible(self, visible, new_button_visible=True):
        self._toggle_panel_button.set_visible(visible)
        self._toggle_popup_button.set_visible(visible)
        self._new_button.set_visible(new_button_visible)
        self._search_button.set_visible(visible)
        self._preview_button.set_visible(visible)

    def set_preview_button_visible(self, visible):
        self._preview_button.set_visible(visible)
        if self._preview_button.get_active():
            self._preview_button.set_active(visible)

    def has_preview_available(self):
        return self._preview_button.get_visible()

    def activate_preview(self):
        in_preview = self._preview_button.get_active()
        self._preview_button.set_active(not in_preview)

    def activate_markup_reference(self):
        if self._editor.get_focus_child() is not None:
            self._on_request_markup_cheatsheet(None)

    def set_utility_buttons_visible(self, visible):
        for button in self._current_utility_buttons:
            button.set_visible(visible)
        for button in self._passive_utility_buttons:
            button.set_visible(False)

    def set_search_button_active(self, active):
        self._search_button.set_active(active)

    def set_panel_button_active(self, active):
        with self._toggle_panel_button.handler_block(self._toggle_handler_id):
            self._toggle_panel_button.set_active(active)

    def set_content_header_title(self, title):
        self._content_title_label.set_label(title)

    def set_content_header_subtitle(self, subtitle):
        if subtitle:
            self._content_subtitle_label.set_visible(True)
            self._content_subtitle_label.set_label(subtitle)
        else:
            self._content_subtitle_label.set_label('')
            self._content_subtitle_label.set_visible(False)

    def set_fullscreen_mode(self, fullscreen_mode):
        if fullscreen_mode:
            self._library_header.get_style_context().add_class('draft-fullscreen-library-header')
            self._list_header.get_style_context().add_class('draft-fullscreen-textlist-header')
            self._content_header.get_style_context().add_class('draft-fullscreen-content-header')
        else:
            self._library_header.get_style_context().remove_class('draft-fullscreen-library-header')
            self._list_header.get_style_context().remove_class('draft-fullscreen-textlist-header')
            self._content_header.get_style_context().remove_class('draft-fullscreen-content-header')

    def set_library_header_visible(self, visible):
        if visible:
            self._library_header.set_visible(True)
            self._failsafe_pack_start(self._library_header,
                                      self._library_buttons)
        else:
            self._library_header.set_visible(False)
            if not self._list_header.get_visible():
                self._failsafe_pack_start(self._content_button_box,
                                          self._library_buttons,
                                          pack_pos=0)
            else:
                self._failsafe_pack_start(self._list_button_box,
                                          self._library_buttons,
                                          pack_pos=0)
        self._update_decorations()

    def set_textlist_header_visible(self, visible):
        if visible:
            self._list_header.set_visible(True)
            self._failsafe_pack_start(self._list_button_box,
                                      self._new_button,
                                      pack_pos=1)
            self._failsafe_pack_start(self._list_button_box,
                                      self._search_button,
                                      pack_pos=2)
            if not self._library_header.get_visible():
                self._failsafe_pack_start(self._list_button_box,
                                          self._library_buttons,
                                          pack_pos=0)
        else:
            self._list_header.set_visible(False)
            self._failsafe_pack_start(self._content_button_box,
                                      self._new_button,
                                      pack_pos=1)
            self._failsafe_pack_start(self._content_button_box,
                                      self._search_button,
                                      pack_pos=2)
            if self._library_header.get_visible():
                self._failsafe_pack_start(self._library_header,
                                          self._library_buttons)
            else:
                self._failsafe_pack_start(self._content_button_box,
                                          self._library_buttons,
                                          pack_pos=0)
        self._update_decorations()

    def _failsafe_pack_start(self, new_parent, child, pack_pos=None):
        visible = child.get_visible()
        old_parent = child.get_parent()
        if old_parent:
            old_parent.remove(child)
        if visible:
            if pack_pos is not None:
                new_parent.pack_start(child, False, False, 0)
                new_parent.reorder_child(child, pack_pos)
            else:
                new_parent.pack_start(child)

    def _update_decorations(self):
        alt_header = self._library_header
        non_header = self._list_header
        if not self._library_header.get_visible():
            alt_header = self._list_header
            non_header = self._library_header
            non_header.props.decoration_layout = ""
            if not self._list_header.get_visible():
                alt_header = self._content_header
                non_header = self._list_header
        non_header.props.decoration_layout = ""

        settings = Gtk.Settings.get_default()
        layout_desc = settings.props.gtk_decoration_layout;
        tokens = layout_desc.split(":", 1)
        alt_set = False
        if len(tokens) > 1:
            self._content_header.props.decoration_layout = ":" + tokens[1]
            if self._content_header is alt_header and tokens[1]:
                alt_set  = True
        else:
            alt_header.props.decoration_layout = ""

        if not alt_set:
            alt_header.props.decoration_layout = tokens[0]

    def set_editor(self, editor):
        self._editor = editor
        self.populate_cheatsheet()

    def populate_cheatsheet(self, markup_type='markdown'):
        entries = []

        # these lists could be automated, but each markup would have its
        # own quirks and support different types of formatting, therefore
        # it makes sense to build one exclusive for each type.
        if markup_type == 'markdown':
            entries= [
                ('<span fgalpha="75%"><b><i>#</i></b></span> Heading 1', 'h1'),
                ('<span fgalpha="75%"><b><i>##</i></b></span> Heading 2', 'h2'),
                ('<span fgalpha="75%"><b><i>###</i></b></span> Heading 3', 'h3'),
                ('<span fgalpha="75%"><b><i>####</i></b></span> Heading 4', 'h4'),
                ('<span fgalpha="75%"><b><i>#####</i></b></span> Heading 5', 'h5'),
                ('<span fgalpha="75%"><b><i>######</i></b></span> Heading 6', 'h6'),
                'sep',
                ('<span fgalpha="75%"><b>---</b></span> Divider', 'divider'),
                'sep',
                ('<span fgalpha="75%"><b>**</b></span>Strong<span fgalpha="75%"><b>**</b></span>', 'strong'),
                ('<span fgalpha="75%"><b>*</b></span>Emphasis<span fgalpha="75%"><b>*</b></span>', 'emphasis'),
                'sep',
                ('<span fgalpha="75%"><b>1.</b></span> Ordered List', 'ordered_list'),
                ('<span fgalpha="75%"><b>-</b></span> Unordered List', 'unordered_list'),
                ('<span fgalpha="75%"><b>&gt;</b></span> Block Quote', 'block_quote'),
                'sep',
                ('<span fgalpha="75%"><b>[</b></span>Link<span fgalpha="75%"><b>]</b></span>', 'link'),
                ('<span fgalpha="75%"><b>![</b></span>Image<span fgalpha="75%"><b>]</b></span>', 'image'),
                ('<span fgalpha="75%"><b>[^</b></span>Footnote<span fgalpha="75%"><b>]</b></span>', 'footnote'),
                'sep',
                ('<span fgalpha="75%"><b>`</b></span>Code<span fgalpha="75%"><b>`</b></span>', 'code'),
                ('<span fgalpha="75%"><b>```</b></span>Code Block<span fgalpha="75%"><b>```</b></span>', 'code_block')
            ]

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for i, entry in enumerate(entries):
            if entry != 'sep':
                model_button = Gtk.ModelButton(entry[0])
                model_button.connect('clicked',
                                     self._editor.handle_generic_insert,
                                     entry[1])
                if not i+1 >= len(entries) and entries[i+1] == 'sep':
                    model_button.set_margin_bottom(12)
                box.add(model_button)

        # FIXME: move this to stylesheets when restyling all popovers.
        box.set_size_request(160, -1)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_left(12)
        box.set_margin_right(12)
        self._cheatsheet_popover.add(box)

        # make cheatsheet buttons use markup enabled GtkLabels
        for button in box.get_children():
            label = button.get_child()
            label.set_halign(Gtk.Align.START)
            label.set_use_markup(True)

        title_label = Gtk.Label(_("Insert Markup"))
        title_label.set_margin_bottom(12)
        title_label.get_style_context().add_class('draft-menu-title')
        box.add(title_label)
        box.reorder_child(title_label, 0)
        box.show_all()
