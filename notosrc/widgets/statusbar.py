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

import re
from gettext import gettext as _

from gi.repository import Gtk, GLib

UPDATE_REGISTRY = []    # registry of functions called when updating state


def registered_for_update(fn):
    """Decorator for registering methods to be called when state update is
    requested.
    """
    UPDATE_REGISTRY.append(fn)
    return fn


class NotoStatusbar(Gtk.Box):
    """A status bar for providing tagging and some mimimal information"""

    __gtype_name__ = 'NotoStatusbar'

    def __repr__(self):
        return '<NotoStatusbar>'

    def __init__(self, editor):
        """Init a new NotoStatusbar for @editor

        @self: NotoStatusbar
        @editor: NotoEditor, the editor which @self serves
        """
        Gtk.Box.__init__(self)
        self.editor = editor
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/statusbar.ui')
        self._set_up_widgets()
        self.get_style_context().add_class('noto-statusbar')

    def _set_up_widgets(self):
        """Set up widgets contained within statusbar"""
        self.overwrite_mode_label = Gtk.Label()
        self.overwrite_mode_label.get_style_context()\
                                 .add_class('noto-statusbar-widget')
        self.pack_end(self.overwrite_mode_label, False, False, 0)

        self.word_count_label = Gtk.Label()
        self.word_count_label.get_style_context()\
                             .add_class('noto-statusbar-widget')
        self.pack_end(self.word_count_label, False, False, 0)

        self.markup_label = Gtk.Label()
        self.markup_label.get_style_context()\
                         .add_class('noto-statusbar-widget')
        self.pack_end(self.markup_label, False, False, 0)

        self.tag_labels = self.builder.get_object('tag_labels')
        self.tag_popover = self.builder.get_object('tag_popover')
        self.tag_popover_list = self.builder.get_object('tag_popover_list')
        self.new_tag_entry = self.builder.get_object('new_tag_entry')
        new_tag_button = self.builder.get_object('new_tag_button')
        clickable = self.builder.get_object('tag_button')

        self.new_tag_entry.connect('activate', self._on_tag_added)
        new_tag_button.connect('clicked', self._on_tag_added)
        clickable.connect('clicked', self._on_labels_clicked)

        self.pack_start(clickable, True, True, 0)

    def update_state(self):
        """Update the state of statusbar to represent the currently visible
        text-view in parent NotoEditor.
        """
        for update_method in UPDATE_REGISTRY:
            update_method(self)

    @registered_for_update
    def update_overwrite_mode(self):
        """Update @self::overwrite_mode_label to denote whether editor is in overwrite
        mode or not.
        """
        if self.editor.view.get_overwrite():
            self.overwrite_mode_label.set_label(_("OVR"))
        else:
            self.overwrite_mode_label.set_label(_("INS"))

    @registered_for_update
    def update_word_count(self):
        """Update @self::word_count_label to the number of words in the current
        document"""
        text = self.editor.get_text()

        # simple regexp to match words. can do better?
        word_rule = re.compile('\S+')
        num_words = len(word_rule.findall(text))
        self.word_count_label.set_label(str(num_words) + ' ' + _("Words"))

    @registered_for_update
    def update_markup(self):
        """Update @self::markup_label to the type of markup being used in
        text view"""
        markup_type = self.editor.markup_type

        if markup_type == 'markdown':
            self.markup_label.set_label(_("Markdown"))

    @registered_for_update
    def update_note_data(self):
        """Updates the note specific information presented by @self, such
        as tags"""
        data_dict = self.editor.current_note_data

        tags = data_dict['tags']
        self._refresh_tag_widget(tags)

        # TODO: Update other information

    def _refresh_tag_widget(self, tags):
        """Add tags from @tags (list) as labels to statusbar as well as refresh
        the state of tag editing popover"""
        def _clear_container(widget):
            assert isinstance(widget, Gtk.Container)
            widget.set_visible(True)

            children = widget.get_children()
            for child in children:
                widget.remove(child)

        _clear_container(self.tag_popover_list)
        _clear_container(self.tag_labels)

        if not tags:
            empty_label = Gtk.Label(_("Add a keyword …"))
            empty_label.get_style_context().add_class('noto-placeholder-label')
            empty_label.set_visible(True)
            self.tag_labels.pack_start(empty_label, False, False, 0)
            self.tag_popover_list.set_visible(False)
            return

        def _add_tag_label(tag):
            label = Gtk.Label()
            label.set_label(tag)
            label.get_style_context()\
                 .add_class('noto-tag-label')
            label.set_visible(True)

            self.tag_labels.pack_start(label, False, False, 0)

        def _append_to_list(tag, icon, action_cb):
            label = Gtk.Label()
            label.set_label(tag)
            label.set_visible(True)

            button = Gtk.Button()
            button.get_style_context().add_class('image-button')
            button.get_style_context().add_class('noto-label-del-button')
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            button.set_image(image)
            button.set_visible(True)

            box = Gtk.Box()
            box.pack_start(label, False, False, 0)
            box.pack_end(button, False, False, 0)
            box.set_visible(True)

            button.connect('clicked', action_cb, label)
            self.tag_popover_list.pack_start(box, False, False, 0)

        for tag in tags:
            _add_tag_label(tag)
            _append_to_list(tag, 'window-close-symbolic', self._on_tag_deleted)

    def _on_labels_clicked(self, button, user_data=None):
        """Handle click on labels"""
        self.tag_popover.popup()
        self.new_tag_entry.grab_focus()

    def _on_tag_added(self, widget, user_data=None):
        """Handle addition of a tag to the note"""
        tag = self.new_tag_entry.get_text()
        if tag:
            self.editor.add_tag(tag)
            self.new_tag_entry.set_text('')

    def _on_tag_deleted(self, widget, label=None):
        """Handle deletion of a tag from the note"""
        tag = label.get_label()
        self.editor.delete_tag(tag)
