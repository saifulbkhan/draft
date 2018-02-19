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

from gi.repository import Gtk, GLib, GObject

UPDATE_REGISTRY = []    # registry of functions called when updating state


def registered_for_update(fn):
    """Decorator for registering methods to be called when state update is
    requested.
    """
    UPDATE_REGISTRY.append(fn)
    return fn


class NotoStatusbar(Gtk.Bin):
    """A status bar for providing tagging and some mimimal information"""

    __gtype_name__ = 'NotoStatusbar'

    __gsignals__ = {
        'word-goal-set': (GObject.SignalFlags.RUN_FIRST,
                          None, (GObject.TYPE_INT,)),
    }

    _word_goal_set = False
    _builder = Gtk.Builder()

    def __repr__(self):
        return '<NotoStatusbar>'

    def __init__(self, editor):
        """Init a new NotoStatusbar for @editor

        @self: NotoStatusbar
        @editor: NotoEditor, the editor which @self serves
        """
        Gtk.Bin.__init__(self)
        self._editor = editor
        self._builder.add_from_resource('/org/gnome/Noto/statusbar.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        """Set up widgets contained within statusbar"""
        self._main_button_box = self._builder.get_object('main_button_box')
        self._main_button_box.get_style_context().add_class('noto-statusbar')
        self.add(self._main_button_box)

        self._word_count_label = self._builder.get_object('word_count_label')
        self._word_goal_label = self._builder.get_object('word_goal_label')
        self._word_goal_complete_label = self._builder.get_object('word_goal_complete_label')
        self._word_goal_popover = self._builder.get_object('word_goal_popover')
        self._word_goal_title = self._builder.get_object('word_goal_title')
        self._goal_set_entry = self._builder.get_object('word_goal_entry')
        self._word_goal_stack = self._builder.get_object('word_goal_stack')
        word_goal_button = self._builder.get_object('word_goal_button')
        goal_edit_button = self._builder.get_object('word_goal_edit_button')
        goal_remove_button = self._builder.get_object('word_goal_remove_button')
        goal_set_button = self._builder.get_object('word_goal_set_button')

        self._word_goal_popover.connect('closed', self._on_goal_popover_closed)
        self._goal_set_entry.connect('changed', self._on_goal_entry_changed)
        self._goal_set_entry.connect('activate', self._on_set_goal)
        word_goal_button.connect('clicked', self._on_word_count_clicked)
        goal_edit_button.connect('clicked', self._on_request_goal_change)
        goal_remove_button.connect('clicked', self._on_request_goal_remove)
        goal_set_button.connect('clicked', self._on_set_goal)

        self._tag_labels = self._builder.get_object('tag_labels')
        self._tag_popover = self._builder.get_object('tag_popover')
        self._tag_popover_list = self._builder.get_object('tag_popover_list')
        self._new_tag_entry = self._builder.get_object('new_tag_entry')
        new_tag_button = self._builder.get_object('new_tag_button')
        clickable = self._builder.get_object('tag_button')

        self._new_tag_entry.connect('activate', self._on_tag_added)
        new_tag_button.connect('clicked', self._on_tag_added)
        clickable.connect('clicked', self._on_labels_clicked)

    def update_state(self):
        """Update the state of statusbar to represent the currently visible
        text-view in parent NotoEditor.
        """
        for update_method in UPDATE_REGISTRY:
            update_method(self)

    def _count_words(self):
        text = self._editor.get_text()
        # simple regexp to match words. can do better?
        word_rule = re.compile('\S+')
        num_words = len(word_rule.findall(text))
        return num_words

    @registered_for_update
    def update_word_count(self):
        """Update @self::word_count_label to the number of words in the current
        document"""
        word_count = self._count_words()
        word_count_string = ('{:,}'.format(word_count))
        self._word_count_label.set_label(word_count_string + ' ' + _("Words"))

        goal = self._editor.current_note_data['word_goal']
        if goal and str(goal) != self._goal_set_entry.get_text():
            self._goal_set_entry.set_text(str(goal))
            self._goal_set_entry.activate()
        self._update_word_goal_state(bool(goal))

    @registered_for_update
    def update_note_data(self):
        """Updates the note specific information presented by @self, such
        as tags"""
        data_dict = self._editor.current_note_data

        tags = data_dict['keywords']
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

        _clear_container(self._tag_popover_list)
        _clear_container(self._tag_labels)

        if not tags:
            empty_label = Gtk.Label(_("Add a keyword …"))
            empty_label.get_style_context().add_class('noto-placeholder-label')
            empty_label.set_visible(True)
            self._tag_labels.pack_start(empty_label, False, False, 0)
            self._tag_popover_list.set_visible(False)
            return

        def _add_tag_label(tag):
            label = Gtk.Label()
            label.set_label(tag)
            label.get_style_context()\
                 .add_class('noto-tag-label')
            label.set_visible(True)

            self._tag_labels.pack_start(label, False, False, 0)

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
            self._tag_popover_list.pack_start(box, False, False, 0)

        for tag in tags:
            _add_tag_label(tag)
            _append_to_list(tag, 'window-close-symbolic', self._on_tag_deleted)

    def _on_labels_clicked(self, button, user_data=None):
        """Handle click on tag labels"""
        self._tag_popover.popup()
        self._new_tag_entry.grab_focus()

    def _on_tag_added(self, widget, user_data=None):
        """Handle addition of a tag to the note"""
        tag = self._new_tag_entry.get_text()
        if tag:
            self._editor.add_tag(tag)
            self._new_tag_entry.set_text('')

    def _on_tag_deleted(self, widget, label=None):
        """Handle deletion of a tag from the note"""
        tag = label.get_label()
        self._editor.delete_tag(tag)

    def _on_word_count_clicked(self, widget, user_data=None):
        """Handle click on word count label"""
        self._word_goal_popover.popup()

    def _update_word_goal_state(self, is_set):
        self._word_goal_set = is_set
        if is_set:
            self._word_goal_title.set_label(_("Writing Goal"))
            self._word_goal_stack.set_visible_child_name('button_mode')
        else:
            self._word_goal_title.set_label(_("Set Writing Goal"))
            self._unset_word_goal()
            self._word_goal_stack.set_visible_child_name('entry_mode')

    def _unset_word_goal(self):
        self._goal_set_entry.set_text('')
        self._word_goal_label.set_visible(False)
        self._word_goal_complete_label.set_visible(False)

    def _set_goal_entry_mode(self, val):
        self._switch_stack_child(int(val))

    def _switch_stack_child(self, child):
        """Set visible stack child as given. 0: entry mode, 1: button mode"""
        children = self._word_goal_stack.get_children()
        active_child = children[child]
        self._word_goal_stack.set_visible_child(active_child)

    def _on_goal_entry_changed(self, widget, user_data=None):
        string = widget.get_text()
        context = widget.get_style_context()
        if string and not string.isdigit():
            context.add_class('error')
        elif context.has_class('error'):
            context.remove_class('error')

    def _on_goal_popover_closed(self, widget, user_data=None):
        parent = self._goal_set_entry.get_parent()
        if self._word_goal_set and \
           self._word_goal_stack.get_visible_child() is parent:
            self._word_goal_stack.set_visible_child_name('button_mode')

    def _on_request_goal_change(self, widget, user_data=None):
        self._word_goal_stack.set_visible_child_name('entry_mode')
        self._goal_set_entry.grab_focus()

    def _on_request_goal_remove(self, widget, user_data=None):
        self._unset_word_goal()
        self._on_request_goal_change(widget)
        self._update_word_goal_state(False)
        self.emit('word-goal-set', 0)

    def _on_set_goal(self, widget, user_data=None):
        current = self._count_words()
        goal = self._goal_set_entry.get_text()

        if not goal or not goal.isdigit() or int(goal) == 0:
            # TODO: warn, goal should be an number
            return

        goal = int(goal)
        done = (current / goal)
        word_goal_string = '<span size="x-large">{:,} Words</span>'.format(goal)
        percent_string = '<span>({:.0%} Complete)</span>'.format(done)
        self._word_goal_label.set_markup(word_goal_string)
        self._word_goal_complete_label.set_markup(percent_string)
        self._word_goal_label.set_visible(True)
        self._word_goal_complete_label.set_visible(True)
        self._update_word_goal_state(True)
        self.emit('word-goal-set', goal)
