from gi.repository import Gtk, GLib
from notosrc.listview import ListView

class NotesView(Gtk.Bin):
    sidebar_width = 300
    def __repr__(self):
        return '<NotesView>'

    def __init__(self, parent):
        Gtk.Bin.__init__(self)
        self.parent_window = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Noto/notesview.ui')
        self.view = self.builder.get_object('listview')
        self._set_up_widgets()

    def _set_up_widgets(self):
        noteslist = self.builder.get_object('noteslist')
        self.add(noteslist)
        self.listview = ListView(self.parent_window)
        self.view.add(self.listview)

    def do_size_allocate(self, allocation):
        Gtk.Bin.do_size_allocate(self, allocation)
