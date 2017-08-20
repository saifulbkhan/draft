import sys
import gi

gi.require_version('Notify', '0.7')
from gi.repository import Gtk, GLib, Gio, Notify

from notosrc.window import ApplicationWindow

class Application(Gtk.Application):
    def __repr__(self):
        return '<Application>'

    def __init__(self):
        Gtk.Application.__init__(self, application_id='org.gnome.Noto',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Noto")
        GLib.set_prgname('noto')
        self._window = None

    def _build_app_menu(self):
        action_entries = [
            ('about', self._about),
            ('quit', self.quit),
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)

    def _about(self):

        def about_response(dialog, response):
            dialog.destroy()

        about = Gtk.AboutDialog()
        about.set_transient_for(self._window)
        about.connect("response", about_response)
        about.show()

    def quit(self):
        self._window.destroy()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init("Noto")
        self._build_app_menu()

    def do_activate(self):
        if not self._window:
            self._window = ApplicationWindow(self)
        self._window.present()
