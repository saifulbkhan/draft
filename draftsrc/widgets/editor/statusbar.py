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
import cairo
import math
from string import whitespace
from gettext import gettext as _

from gi.repository import Gtk, GLib, GObject, Gdk, Pango

UPDATE_REGISTRY = []    # registry of functions called when updating state


def registered_for_update(fn):
    """Decorator for registering methods to be called when state update is
    requested.
    """
    UPDATE_REGISTRY.append(fn)
    return fn


class DraftStatusbar(Gtk.Bin):
    """A status bar for providing tagging and some mimimal information"""

    __gtype_name__ = 'DraftStatusbar'

    __gsignals__ = {
        'word-goal-set': (GObject.SignalFlags.RUN_FIRST,
                          None, (GObject.TYPE_INT,)),
    }

    _word_goal_set = False
    _word_goal_ratio_accomplished = 0
    _builder = Gtk.Builder()

    def __repr__(self):
        return '<DraftStatusbar>'

    def __init__(self, editor):
        """Init a new DraftStatusbar for @editor

        @self: DraftStatusbar
        @editor: DraftEditor, the editor which @self serves
        """
        Gtk.Bin.__init__(self)
        self._editor = editor
        self._builder.add_from_resource('/org/gnome/Draft/statusbar.ui')
        self._set_up_widgets()

    def _set_up_widgets(self):
        """Set up widgets contained within statusbar"""
        self._main_button_box = self._builder.get_object('main_button_box')
        self._main_button_box.get_style_context().add_class('draft-statusbar')
        self.add(self._main_button_box)

        self._word_count_label = self._builder.get_object('word_count_label')
        self._goal_label = self._builder.get_object('goal_label')
        self._word_count_stack = self._builder.get_object('word_count_stack')
        self._word_goal_label = self._builder.get_object('word_goal_label')
        self._word_goal_overlay = self._builder.get_object('word_goal_overlay')
        self._word_goal_drawing_area = self._builder.get_object('word_goal_drawing_area')
        self._word_goal_popover = self._builder.get_object('word_goal_popover')
        self._word_goal_title = self._builder.get_object('word_goal_title')
        self._goal_set_entry = self._builder.get_object('word_goal_entry')
        self._word_goal_stack = self._builder.get_object('word_goal_stack')
        self._word_goal_overlay = self._builder.get_object('word_goal_overlay')
        word_goal_button = self._builder.get_object('word_goal_button')
        goal_edit_button = self._builder.get_object('word_goal_edit_button')
        goal_remove_button = self._builder.get_object('word_goal_remove_button')
        goal_set_button = self._builder.get_object('word_goal_set_button')

        self._word_count_overlay_label = Gtk.Label()
        self._word_count_overlay_label.set_justify(Gtk.Justification.CENTER)
        self._word_goal_overlay.add_overlay(self._word_count_overlay_label)

        self._word_goal_popover.connect('closed', self._on_goal_popover_closed)
        self._word_goal_drawing_area.connect('draw', self._on_goal_draw)
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
        self._tag_popover.connect('closed', self._on_tag_popover_closed)
        new_tag_button.connect('clicked', self._on_tag_added)
        clickable.connect('clicked', self._on_labels_clicked)

    def update_state(self):
        """Update the state of statusbar to represent the currently visible
        text-view in parent DraftEditor.
        """
        for update_method in UPDATE_REGISTRY:
            update_method(self)

    def show_tag_editor(self):
        self._on_labels_clicked(None, None)

    def show_goal_editor(self):
        self._on_word_count_clicked(None, None)

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

        goal = self._editor.current_text_data.word_goal
        if goal and str(goal) != self._goal_set_entry.get_text():
            self._goal_set_entry.set_text(str(goal))
            self._goal_set_entry.activate()
        self._update_word_goal_state(bool(goal))

        if self._word_goal_set:
            done = word_count / goal

            if self._word_goal_ratio_accomplished < 1 and done >= 1:
                self._word_count_stack.set_visible_child(self._goal_label)
                GLib.timeout_add(1000,
                                 self._word_count_stack.set_visible_child,
                                 self._word_count_label)

            self._word_goal_ratio_accomplished = done
            overlay_string = '<span font_size="xx-large"><b>{:,}</b></span>\nwords'.format(word_count)
            self._word_count_overlay_label.set_markup(overlay_string)

    @registered_for_update
    def update_text_data(self):
        """Updates the text specific information presented by @self, such
        as tags"""
        tags = self._editor.current_text_data.tags
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
            empty_label = Gtk.Label(_("Add a tag …"))
            empty_label.get_style_context().add_class('draft-placeholder-label')
            empty_label.set_visible(True)
            self._tag_labels.pack_start(empty_label, False, False, 0)
            self._tag_popover_list.set_visible(False)
            return

        def _add_tag_label(tag):
            label = Gtk.Label()
            label.set_label(tag)
            label.get_style_context()\
                 .add_class('draft-tag-label')
            label.set_visible(True)

            self._tag_labels.pack_start(label, False, False, 0)

        def _append_to_list(tag, icon, action_cb):
            label = Gtk.Label()
            label.set_label(tag)
            label.set_visible(True)

            button = Gtk.Button()
            button.get_style_context().add_class('image-button')
            button.get_style_context().add_class('draft-label-del-button')
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
        """Handle addition of a tag to the text"""
        tag_text = self._new_tag_entry.get_text()
        tags = re.split(' |\t|,', tag_text)
        for tag in tags:
            if tag:
                self._editor.add_tag(tag)
        self._new_tag_entry.set_text('')

    def _on_tag_deleted(self, widget, label=None):
        """Handle deletion of a tag from the text"""
        tag = label.get_label()
        self._editor.delete_tag(tag)

    def _on_tag_popover_closed(self, widget):
        self._editor.fullscreen_statusbar_reveal(False)

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
        self._word_goal_overlay.set_visible(False)

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
        self._editor.fullscreen_statusbar_reveal(False)

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
        self._word_goal_ratio_accomplished = done
        overlay_string = '<span font_size="xx-large"><b>{:,}</b></span>\nwords'.format(current)
        self._word_count_overlay_label.set_markup(overlay_string)
        goal_string = 'of at least\n<b>{:,}</b> words'.format(goal)
        self._word_goal_label.set_markup(goal_string)
        self._word_goal_label.set_visible(True)
        self._word_goal_overlay.show_all()
        self._update_word_goal_state(True)
        self.emit('word-goal-set', goal)

    def _on_goal_draw(self, widget, cr):
        context = widget.get_style_context()

        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        Gtk.render_background(context, cr, 0, 0, width, height)

        xc, yc = width/2.0, height/2.0
        radius = min(height, width) / 2.0
        angle1 = angle2 = - (math.pi / 2.0)
        ratio = self._word_goal_ratio_accomplished
        fg_color = context.get_color(context.get_state())
        bg_color = Gdk.RGBA()
        has_color, bg_color = context.lookup_color('theme_bg_color')
        has_color, completion_color = context.lookup_color('theme_selected_bg_color')

        # Add a faded circle first
        cr.move_to(xc, yc)
        fg_color.alpha = 0.1
        Gdk.cairo_set_source_rgba(cr, fg_color)
        cr.arc(xc, yc, radius, 0, 2 * math.pi)
        cr.fill()

        # Add the goal completion circle
        if ratio > 0:
            if ratio >= 1:
                ratio = 1
                has_color, completion_color = context.lookup_color('success_color')
                completion_color.alpha = 0.7
            angle2 = (ratio * math.pi * 2.0) - (math.pi / 2.0)
            cr.move_to(xc, yc)
            Gdk.cairo_set_source_rgba(cr, completion_color)
            cr.arc(xc, yc, radius, angle1, angle2)
            cr.fill()

        # Add an inner circle of bg color
        cr.move_to(xc, yc)
        bg_color.alpha = 1.0
        if ratio >= 1:
            bg_color.alpha = 0.8
        Gdk.cairo_set_source_rgba(cr, bg_color)
        cr.arc(xc, yc, radius - 16, 0, 2 * math.pi)
        cr.fill()

        return False