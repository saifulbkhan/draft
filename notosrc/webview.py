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

from gi.repository import Gtk, WebKit2 as WebKit

class WebView(Gtk.Box):
    def __repr__(self):
        return '<WebView>'

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        manager = self._set_up_content_manager()
        self.view = WebKit.WebView.new_with_user_content_manager(manager)
        self.view.connect('decide_policy', self._on_decision_request)
        self._webview_settings()
        self._set_up_widgets()

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

    def _webview_settings(self):
        settings = self.view.get_settings()
        # settings.set_enable_write_console_messages_to_stdout(True)

    def _set_up_widgets(self):
        scrollable_window = Gtk.ScrolledWindow()
        scrollable_window.hexpand = True
        scrollable_window.vexpand = True

        scrollable_window.add(self.view)
        self.pack_start(scrollable_window, True, True, 0)

    def _on_decision_request(self, *args):
        webview, policy_decision, decision_type = args
        # Hack to prevent webview from navigating to other pages
        if webview.is_editable():
            policy_decision.use()
            webview.set_editable(False)
        else:
            policy_decision.ignore()
        return True
