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
from gi.repository import Gtk, GLib

from draftsrc import export
from draftsrc.widgets.editor.editor import DraftEditor
from draftsrc.widgets.preview import DraftPreview
from draftsrc.parsers.markup import render_markdown
from draftsrc.parsers.webstrings import html_string


# TODO: Make this a horizontal box to support side-by-side editing
class ContentView(Gtk.Bin):
    _last_content_state = 'editor'
    _current_html_content = []

    def __repr__(self):
        return '<ContentView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Draft/contentview.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        self.content_stack = self.builder.get_object('content_stack')
        self.content_stack.set_hexpand(True)
        self.add(self.content_stack)

        self.content_editor = DraftEditor(self.parent_window, self)
        self.content_stack.add_titled(self.content_editor, 'editor', 'Editor')

        self.content_preview = DraftPreview(self.parent_window)
        self.content_stack.add_titled(self.content_preview, 'preview', 'Preview')
        self.content_preview.connect('view-changed', self._on_content_preview_changed)

        self.empty_state = _DraftEmptyView()
        self.content_stack.add_titled(self.empty_state, 'empty', 'Empty')

        self.empty_trash_state = _DraftEmptyTrashView()
        self.content_stack.add_titled(self.empty_trash_state, 'trash', 'Trash')

        self.content_stack.set_visible_child_name('editor')

    def preview_content(self):
        html_contents = {}
        self._current_html_content = []
        preview_data, current_text_id = self.content_editor.get_preview_data()
        for row in preview_data:
            text_id, markup_type, markup_content = row
            if markup_type == 'markdown':
                html_content = render_markdown(markup_content)
                self._current_html_content.append(html_content)
                html_content = html_string % html_content
                html_contents[text_id] = html_content

        self.content_preview.load_html(html_contents, current_text_id)

    def in_preview_mode(self):
        return self.content_stack.get_visible_child_name() == 'preview'

    def preview_toggled(self):
        if self.content_stack.get_visible_child_name() == 'editor':
            self.content_stack.set_visible_child_name('preview')
            self.preview_content()
            self._last_content_state = 'preview'
        else:
            self.content_stack.set_visible_child_name('editor')
            self._last_content_state = 'editor'

    def html_export_requested(self):
        suggested_title = self.content_editor.get_export_title()
        export.handle_html_export_request(self._current_html_content,
                                          suggested_title)

    def set_empty_group_state(self):
        self.empty_state.update_labels()
        self._set_empty_state()

    def set_empty_collection_state(self):
        self.empty_state.update_labels(empty_collection=True)
        self._set_empty_state()

    def set_empty_recent_state(self):
        self.empty_state.update_labels(empty_recent=True)
        self._set_empty_state()

    def set_empty_selection_state(self):
        self.empty_state.update_labels(empty_selection=True)
        self._set_empty_state()

    def _set_empty_state(self):
        if self.content_stack.get_visible_child_name() != 'empty':
            current_state = self.content_stack.get_visible_child_name()
            if current_state in ['editor', 'preview']:
                self._last_content_state = current_state
            self.content_stack.set_visible_child_name('empty')

    def set_empty_trashed_group_state(self):
        self.empty_trash_state.update_labels()
        self._set_empty_trash_state()

    def set_empty_trash_state(self):
        self.empty_trash_state.update_labels(empty_trash=True)
        self._set_empty_trash_state()

    def set_empty_trash_texts_state(self):
        self.empty_trash_state.update_labels(empty_trash_texts=True)
        self._set_empty_trash_state()

    def _set_empty_trash_state(self):
        if self.content_stack.get_visible_child_name() != 'trash':
            current_state = self.content_stack.get_visible_child_name()
            if current_state in ['editor', 'preview']:
                self._last_content_state = current_state
            self.content_stack.set_visible_child_name('trash')

    def set_last_content_state(self):
        self.content_stack.set_visible_child_name(self._last_content_state)

    def _on_content_preview_changed(self, widget, offset):
        if offset == -1:
            self.content_editor.multi_mode_prev()
        elif offset == 1:
            self.content_editor.multi_mode_next()


class _DraftEmptyView(Gtk.Bin):
    """A container housing elements that are shown during empty states for the
    application. Valid empty states are when there are no groups or texts in
    the database (for eg. when the application is being used on a system for
    the first time) or when there are no texts in a group.
    """

    def __repr__(self):
        return '<DraftEmptyView>'

    def __init__(self):
        Gtk.Bin.__init__(self)

        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/org/gnome/Draft/contentview.ui')

        util_box = self._builder.get_object('info_box')
        util_box.set_visible(True)

        self.title_label = self._builder.get_object('title_label')
        self.info_label = self._builder.get_object('info_label')
        self.new_group_button = self._builder.get_object('new_group_button')
        self.new_text_button = self._builder.get_object('new_text_button')

        self.add(util_box)

    def update_labels(self, empty_collection=False,
                      empty_recent=False, empty_selection=False):
        self.new_group_button.set_visible(True)
        self.new_text_button.set_visible(True)

        title_text = _("No Texts in this Group")
        info_text = _("Create a subgroup or add a text and start writing")
        if empty_collection:
            title_text = _("Collection is empty")
            info_text = _("Create a group to organize your work or create a text to start writing")
        elif empty_recent:
            self.new_group_button.set_visible(False)
            self.new_text_button.set_visible(False)
            title_text = _("Nothing here yet")
            info_text = _("No recently edited texts were found")
        elif empty_selection:
            self.new_group_button.set_visible(False)
            self.new_text_button.set_visible(False)
            title_text = _("No Text Selected")
            info_text = ""

        self.title_label.set_label(title_text)
        self.info_label.set_label(info_text)


class _DraftEmptyTrashView(Gtk.Bin):
    """A container housing empty state notification elements for application's
    trash"""

    def __repr__(self):
        return '<DraftEmptyTrashView>'

    def __init__(self):
        Gtk.Bin.__init__(self)

        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/org/gnome/Draft/contentview.ui')

        trash_box = self._builder.get_object('trash_box')
        trash_box.set_visible(True)

        self.trash_title_label = self._builder.get_object('trash_title_label')
        self.add(trash_box)

    def update_labels(self, empty_trash=False, empty_trash_texts=False):
        trash_title = _("Empty Group")
        if empty_trash:
            trash_title = _("Trash is Empty")
        if empty_trash_texts:
            trash_title = _("No Texts in Trash")

        self.trash_title_label.set_label(trash_title)
