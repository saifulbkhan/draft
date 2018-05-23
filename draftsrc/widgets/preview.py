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

from os import environ, path
from subprocess import call

import gi
gi.require_version('WebKit2', '4.0')
gi.require_version('WkJsCore', '0.1')
from gi.repository import Gtk, GLib, GObject, Gdk, WebKit2 as WebKit, WkJsCore

from draftsrc.defs import DATA_DIR

DRAFT_DIR = 'file://' + path.join(DATA_DIR, 'draft')


class DraftPreview(Gtk.Box):
    __gtype_name__ = 'DraftPreview'

    __gsignals__ = {
        'view-changed': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         (GObject.TYPE_INT,))
    }

    class _ViewData(object):
        scroll_offset = 0

    _open_views = {}
    _view_order = []

    def __repr__(self):
        return '<DraftPreview>'

    def __init__(self, main_window):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.scrollOffset = 0;
        self.main_window = main_window
        self._set_up_widgets()

    def _set_up_widgets(self):
        self._manager = self._set_up_content_manager()
        self.connect('key-press-event', self._on_key_pressed)

        self._view_stack = Gtk.Stack()
        self._view_stack.set_transition_duration(500)
        self.pack_start(self._view_stack, True, True, 0)

    def _set_up_content_manager(self):
        user_content_manager = WebKit.UserContentManager()
        home = environ.get('HOME')
        # This would only work on UNIX filesystems. Maybe fix this?
        css_path = path.join(home, '.local/share/draft/styles/webview.css')
        with open(css_path) as f:
            css_str = f.read()
            user_stylesheet = WebKit.UserStyleSheet(
                css_str,
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserStyleLevel.USER,
                None,
                None
            )
            user_content_manager.add_style_sheet(user_stylesheet)
        return user_content_manager

    def add_view(self, id):
        webview = WebKit.WebView.new_with_user_content_manager(self._manager)
        webview.connect('decide_policy', self._on_decision_request)
        webview.connect('load_changed', self._on_load_changed)
        webview.connect('unmap', self._on_unmapped)

        scrollable_window = Gtk.ScrolledWindow()
        scrollable_window.hexpand = True
        scrollable_window.vexpand = True
        scrollable_window.add(webview)
        scrollable_window.show_all()
        scrollable_window.connect('scroll-event', self._on_scroll_event)

        self._open_views[webview] = self._ViewData()
        self._view_stack.add_named(scrollable_window, id)

        return scrollable_window

    def load_html(self, html_contents, current):
        # clear last order
        self._view_order = []

        for id in html_contents:
            scrolled = self._view_stack.get_child_by_name(id)
            if not scrolled:
                scrolled = self.add_view(id)

            if id == current:
                self._view_stack.set_visible_child(scrolled)

            webview = scrolled.get_child().get_child()
            webview.set_editable(True)
            GLib.idle_add(webview.load_html, html_contents[id], DRAFT_DIR)
            self._view_order.append(id)

    @staticmethod
    def open_link(link):
        """Opens a URL in default browser, assumes `xdg-open` command is
        available"""
        call(['xdg-open', link])

    def _view_next(self):
        current = self._view_stack.get_visible_child_name()
        index = -1
        try:
            index = self._view_order.index(current)
        except ValueError as err:
            # TODO: (notify) current visible child not in order list.
            pass
        next_index = index + 1
        if next_index < len(self._view_order):
            next = self._view_order[next_index]
            next_child = self._view_stack.get_child_by_name(next)
            webview = next_child.get_child().get_child()
            self._scroll_webview_to(webview, 0)
            self._view_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP)
            self._view_stack.set_visible_child(next_child)
            self.emit('view-changed', 1)

    def _view_prev(self):
        current = self._view_stack.get_visible_child_name()
        index = -1
        try:
            index = self._view_order.index(current)
        except ValueError as err:
            # TODO: (notify) current visible child not in order list.
            pass
        prev_index = index - 1
        if not prev_index < 0:
            prev = self._view_order[prev_index]
            prev_child = self._view_stack.get_child_by_name(prev)
            webview = prev_child.get_child().get_child()
            self._scroll_webview_to(webview, 'document.documentElement.scrollHeight')
            self._view_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_DOWN)
            self._view_stack.set_visible_child(prev_child)
            self.emit('view-changed', -1)

    def _scroll_webview_to(self, webview, scroll_to):
        js_string = 'window.scrollTo(0, %s);' % scroll_to
        webview.run_javascript(js_string, None, None, None)

    def _on_decision_request(self, *args):
        webview, policy_decision, decision_type = args
        # Hack to prevent webview from navigating to other pages
        if webview.is_editable():
            policy_decision.use()
            webview.set_editable(False)
        elif decision_type == WebKit.PolicyDecisionType.RESPONSE:
            uri = webview.get_uri()
            self.open_link(uri)
            policy_decision.ignore()
        return True

    def _on_load_changed(self, *args):
        webview, load_event = args
        view_data = self._open_views.get(webview)
        if not view_data:
            return

        if load_event == WebKit.LoadEvent.FINISHED:
            self._scroll_webview_to(webview, view_data.scroll_offset)

    def _on_unmapped(self, *args):
        webview = args[0]
        view_data = self._open_views.get(webview)
        if not view_data:
            return

        def javascript_finished_cb(source_object, res, user_data):
            js_result = source_object.run_javascript_finish(res)
            result_processor = WkJsCore.Result.new(js_result)
            assert result_processor.get_result_type() == WkJsCore.Type.NUMBER
            view_data.scroll_offset = result_processor.process_result_as_number()

        webview.run_javascript(
            'window.scrollY',
            None,
            javascript_finished_cb,
            None
        )

    def _on_scroll_event(self, scrolled, scroll_event):
        vadj = scrolled.get_vadjustment()
        _, del_x, del_y = scroll_event.get_scroll_deltas()
        if scroll_event.direction == Gdk.ScrollDirection.UP or del_y < 0:
            self._view_prev()
        elif scroll_event.direction == Gdk.ScrollDirection.DOWN or del_y > 0:
            self._view_next()

    def _on_key_pressed(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        # TODO: Add shortcuts to textview
        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_F9:
                self.main_window.toggle_panels()
