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

import sys
import gi

gi.require_version('Notify', '0.7')
gi.require_version('GtkSource', '3.0')
from gi.repository import Gtk, GLib, Gio, Gdk, Notify, GtkSource

from draftsrc.window import ApplicationWindow
from draftsrc.widgets import preview
from draftsrc.defs import VERSION as app_version
from draftsrc.file import init_storage
from draftsrc.db import init_db

class Application(Gtk.Application):
    def __repr__(self):
        return '<Application>'

    def __init__(self):
        Gtk.Application.__init__(self, application_id='org.gnome.Draft',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Draft")
        GLib.set_prgname('draft')
        init_storage()
        init_db(app_version)
        self._init_style()
        self._window = None
        self._settings = Gio.Settings.new('org.gnome.Draft')

    def _init_style(self):
        css_provider_file = Gio.File.new_for_uri(
            'resource:///org/gnome/Draft/application.css')
        css_provider = Gtk.CssProvider()
        css_provider.load_from_file(css_provider_file)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_app_menu(self):
        self.builder.add_from_resource('/org/gnome/Draft/appmenu.ui')
        appmenu = self.builder.get_object('appmenu')
        self.set_app_menu(appmenu)

        action_entries = [
            ('preferences', self._preferences),
            ('about', self._about),
            ('quit', self.quit),
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)

    def _preferences(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Draft/preferences.ui')
        preferences_dialog = builder.get_object('preferences_dialog')
        dark_ui_switch = builder.get_object('dark_ui_switch')
        color_scheme_label = builder.get_object('color_scheme_label')
        color_scheme_scrolled = builder.get_object('color_scheme_scrolled')
        preview_stylesheet_label = builder.get_object('preview_stylesheet_label')
        preview_stylesheet_scrolled = builder.get_object('preview_stylesheet_scrolled')
        font_chooser_button = builder.get_object('font_chooser_button')
        typewriter_mode_label = builder.get_object('typewriter_mode_label')
        typewriter_mode_options = builder.get_object('typewriter_mode_options')

        def preferences_response(dialog, response):
            preferences_dialog.destroy()

        def dark_ui_state_switched(switch, state):
            self._settings.set_boolean('dark-ui', state)

        def scheme_button_clicked(button):
            color_scheme_label.set_label(button.get_label())
            color_scheme_id = button_scheme_pairs.get(button)
            self._settings.set_string('color-scheme', color_scheme_id)

        def style_button_clicked(button):
            preview_stylesheet_label.set_label(button.get_label())
            stylesheet = button_style_pairs.get(button)
            self._settings.set_string('stylesheet', stylesheet)

        def editor_font_set(font_button, user_data=None):
            font_name = font_button.get_font()
            self._settings.set_string('editor-font', font_name)

        def typewriter_mode_selected(button, user_data=None):
            typewriter_mode_label.set_label(button.props.text)
            index = typewriter_mode_options.child_get_property(button,
                                                               'position')
            self._settings.set_enum('typewriter-mode', index)

        dark_ui_state = self._settings.get_boolean('dark-ui')
        dark_ui_switch.set_state(dark_ui_state)
        dark_ui_switch.connect('state-set', dark_ui_state_switched)

        current_scheme_id = self._settings.get_string('color-scheme')
        button_scheme_pairs = {}
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme_ids = style_manager.get_scheme_ids()
        if scheme_ids:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for scheme_id in scheme_ids:
                scheme = style_manager.get_scheme(scheme_id)
                button = Gtk.ModelButton()
                button.set_label(scheme.get_name())
                button.get_child().set_halign(Gtk.Align.START)
                button.connect('clicked', scheme_button_clicked)
                box.add(button)
                button_scheme_pairs[button] = scheme_id

                if scheme_id == current_scheme_id:
                    color_scheme_label.set_label(scheme.get_name())

            box.show_all()
            color_scheme_scrolled.add(box)

        current_stylesheet = self._settings.get_string('stylesheet')
        available_styles = preview.get_available_styles()
        button_style_pairs = {}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for stylesheet in available_styles:
            button = Gtk.ModelButton()
            button.set_label(available_styles.get(stylesheet))
            button.get_child().set_halign(Gtk.Align.START)
            button.connect('clicked', style_button_clicked)
            box.add(button)
            button_style_pairs[button] = stylesheet

            if stylesheet == current_stylesheet:
                preview_stylesheet_label.set_label(available_styles.get(stylesheet))

        box.show_all()
        preview_stylesheet_scrolled.add(box)

        current_font = self._settings.get_string('editor-font').strip("'")
        font_chooser_button.set_font(current_font)
        font_chooser_button.connect('font-set', editor_font_set)

        current_typewriter_mode = self._settings.get_enum('typewriter-mode')
        for button in typewriter_mode_options.get_children():
            button.connect('clicked', typewriter_mode_selected)
            index = typewriter_mode_options.child_get_property(button,
                                                               'position')
            if index == current_typewriter_mode:
                typewriter_mode_label.set_label(button.props.text)

        preferences_dialog.set_transient_for(self._window)
        preferences_dialog.connect('response', preferences_response)
        preferences_dialog.show()

    def _about(self, action, param):

        def about_response(dialog, response):
            dialog.destroy()

        self.builder.add_from_resource('/org/gnome/Draft/aboutdialog.ui')
        about = self.builder.get_object('about_dialog')
        about.set_transient_for(self._window)
        about.connect("response", about_response)
        about.show()

    def quit(self, action=None, param=None):
        self._window.destroy()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init("Draft")
        self.builder = Gtk.Builder()
        self._build_app_menu()

    def do_activate(self):
        if not self._window:
            self._window = ApplicationWindow(self, self._settings)
        self._window.present()
