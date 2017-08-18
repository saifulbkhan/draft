import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class Application(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id='org.gnome.Noto',
                         **kwargs)

    def do_activate(self):
        window = Gtk.ApplicationWindow.new(self)
        window.set_default_size(200, 200)
        window.set_title('Noto')
        window.present()
