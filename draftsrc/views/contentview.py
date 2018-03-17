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

from draftsrc.widgets.editor import DraftEditor
from draftsrc.widgets.preview import DraftPreview
from draftsrc.parsers.markup import render_markdown


# TODO: Make this a horizontal box to support side-by-side editing
class ContentView(Gtk.Bin):
    _last_content_state = 'editor'

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

        self.empty_state = _DraftEmptyView()
        self.content_stack.add_titled(self.empty_state, 'empty', 'Empty')

        self.content_stack.set_visible_child_name('editor')

    def preview_content(self):
        markup = self.content_editor.get_text()
        markup_type = self.content_editor.markup_type
        if markup_type == 'markdown':
            render_markdown(markup, self.content_preview.view)

    def in_preview_mode(self):
        return self.content_stack.get_visible_child_name() == 'preview'

    def preview_toggled(self):
        if self.content_stack.get_visible_child_name() == 'editor':
            self.content_stack.set_visible_child_name('preview')
            self.preview_content()
        else:
            self.content_stack.set_visible_child_name('editor')

    def set_empty_group_state(self):
        self.empty_state.update_labels()

        if self.content_stack.get_visible_child_name() != 'empty':
            self._last_content_state = self.content_stack.get_visible_child_name()
            self.content_stack.set_visible_child_name('empty')

    def set_empty_collection_state(self):
        self.empty_state.update_labels(empty_collection=True)

        if self.content_stack.get_visible_child_name() != 'empty':
            self._last_content_state = self.content_stack.get_visible_child_name()
            self.content_stack.set_visible_child_name('empty')

    def set_last_content_state(self):
        self.content_stack.set_visible_child_name(self._last_content_state)


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

        util_box = self._builder.get_object('util_box')
        util_box.set_visible(True)

        self.title_label = self._builder.get_object('title_label')
        self.info_label = self._builder.get_object('info_label')
        new_group_button = self._builder.get_object('new_group_button')
        new_text_button = self._builder.get_object('new_text_button')

        self.add(util_box)

    def update_labels(self, empty_collection=False):
        title_text = _("This group has no texts")
        info_text = _("Create a subgroup for finer structure or create a text to start writing")
        if empty_collection:
            title_text = _("Your collection is empty")
            info_text = _("Create a group to organize your work or create a text to start writing")

        self.title_label.set_label(title_text)
        self.info_label.set_label(info_text)
