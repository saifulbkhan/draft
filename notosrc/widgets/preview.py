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

import gi
gi.require_version('WebKit2', '4.0')
gi.require_version('WkJsCore', '0.1')

from gi.repository import Gtk, Gdk, WebKit2 as WebKit, WkJsCore


class NotoPreview(Gtk.Box):
    __gtype_name__ = 'NotoPreview'

    def __repr__(self):
        return '<NotoPreview>'

    def __init__(self, main_window):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.scrollOffset = 0;
        self.main_window = main_window
        self._set_up_widgets()

    def _set_up_widgets(self):
        manager = self._set_up_content_manager()
        self.view = WebKit.WebView.new_with_user_content_manager(manager)
        self.view.connect('decide_policy', self._on_decision_request)
        self.view.connect('load_changed', self._on_load_changed)
        self.view.connect('unmap', self._on_unmapped)
        self.connect('key-press-event', self._on_key_pressed)

        scrollable_window = Gtk.ScrolledWindow()
        scrollable_window.hexpand = True
        scrollable_window.vexpand = True

        scrollable_window.add(self.view)
        self.pack_start(scrollable_window, True, True, 0)

    def _set_up_content_manager(self):
        user_content_manager = WebKit.UserContentManager()
        home = environ.get('HOME')
        # This would only work on UNIX filesystems. Maybe fix this?
        css_path = path.join(home, '.local/share/noto/styles/webview.css')
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

    # TODO: Maybe we need this for debugging only
    def _webview_settings(self):
        settings = self.view.get_settings()
        # settings.set_enable_write_console_messages_to_stdout(True)

    def _on_decision_request(self, *args):
        webview, policy_decision, decision_type = args
        # Hack to prevent webview from navigating to other pages
        if webview.is_editable():
            policy_decision.use()
            webview.set_editable(False)
        else:
            policy_decision.ignore()
        return True

    def _on_load_changed(self, *args):
        webview, load_event = args
        if load_event == WebKit.LoadEvent.FINISHED:
            js_string = 'window.scrollTo(0, %s);' % self.scrollOffset
            webview.run_javascript(js_string, None, None, None)

    def _on_unmapped(self, *args):
        webview = args[0]

        def javascript_finished_cb(source_object, res, user_data):
            js_result = source_object.run_javascript_finish(res)
            result_processor = WkJsCore.Result.new(js_result)
            assert result_processor.get_result_type() == WkJsCore.Type.NUMBER
            self.scrollOffset = result_processor.process_result_as_number()

        webview.run_javascript(
            'window.scrollY',
            None,
            javascript_finished_cb,
            None
        )

    def _on_key_pressed(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        # TODO: Add shortcuts to textview
        if not event_and_modifiers:
            if event.keyval == Gdk.KEY_F9:
                self.main_window.toggle_panel()
