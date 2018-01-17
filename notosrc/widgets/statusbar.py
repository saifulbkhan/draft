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


class NotoStatusbar(Gtk.Statusbar):
    """A status bar for providing commentary and some mimimal utility"""
    flash_timeout = 500     # time in miliseconds for which message is flashed

    # TODO: Add tags button

    def __repr__(self):
        return '<NotoStatusbar>'

    def __init__(self, editor):
        """Init a new NotoStatusbar for @editor

        @self: NotoStatusbar
        @editor: NotoEditor, the editor which @self serves
        """
        Gtk.Statusbar.__init__(self)
        self.editor = editor
        self._set_up_widgets()

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

    def add_message(self, msg, flash_only=False):
        """Adds a new @msg, to @self's message stack, using visible text-view's
        name as context. Optionally, a @flash_only parameter makes @msg
        get popped out of message stack (and hence no longer visible) after
        a time period of @self::timeout.

        @self: NotoStatusbar
        @msg: string, a message to be pushed in context to visible textview
        @flash_only: boolean, whether @msg should be remvoved after timeout
        """
        context = self.editor.editor_stack.get_visible_child_name()
        context_id = self.get_context_id(context)
        msg_id = self.push(context_id, msg)

        if flash_only:
            GLib.timeout_add(self.flash_timeout,
                             self.remove, context_id, msg_id)
