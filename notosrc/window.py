from gi.repository import Gtk, Gdk, Gio, GLib
from gettext import gettext as _

class ApplicationWindow(Gtk.ApplicationWindow):
    def __repr__(self):
        return '<ApplicationWindow>'

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Noto")
        if Gdk.Screen.get_default().get_height() < 700:
            self.maximize()
        else:
            self.set_size_request(960, 640)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name("noto")
        self.hsize_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

