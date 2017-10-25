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

from gettext import gettext as _
from gi.repository import GLib, GObject, Gtk

from notosrc import data


class TreeStore(Gtk.TreeStore):

    def __repr__(self):
        return '<TreeStore>'

    def __init__(self):
        Gtk.TreeStore.__init__(
            self,
            GObject.TYPE_STRING,        # title or name
            GObject.TYPE_STRING,        # tags or number of items
            GObject.TYPE_STRING,        # last modified
            GObject.TYPE_STRING,        # hash-id for file or folder name
            GObject.TYPE_BOOLEAN        # whether in trash or not
        )
        self._load_data()

    def _load_data(self):
        with data.session_scope() as session:
            notes = data.fetch_notes_not_in_notebooks(session)
            notebooks = data.fetch_notebooks_not_in_notebook(session)
            rows = self.rows_for_notes(notes)
            for row in rows:
                if not row[4]:
                    self.append(None, row)
            # TODO: Insert notebooks and their notes

    def new_note_request(self):
        with data.session_scope() as session:
            note = data.create_note(_("Unititled"), session)
            note_row = self.row_for_note(note)
            return self.append(None, note_row)

    def new_notebook_request(self):
        with data.session_scope() as session:
            notebook = data.create_notebook(_("Untitled"), session)
            notebook_row = self.row_for_notebook(notebook)
            self.append(None, notebook_row)

    def row_for_note(self, note):
        tag_str = ' '.join(map(lambda x: x.keyword, note.tags))
        row = [note.title,
               tag_str,
               note.get_last_modified_relative_time(),
               note.hash_id,
               bool(note.in_trash)]
        return row

    def rows_for_notes(self, notes):
        rows = []
        for note in notes:
            row = self.row_for_note(note)
            rows.append(row)
        return rows

    def row_for_notebook(self, notebook):
        items = len(notebook.notes) + len(notebook.notebooks)
        row = [notebook.name,
               str(items),
               notebook.get_last_modified_relative_time(),
               notebook.hash_id,
               bool(notebook.in_trash)]
        return row

    def rows_for_notebooks(self, notebooks):
        rows = []
        for notebook in notebooks:
            row = self.row_for_notebook(notebook)
            rows.append(row)
        return rows
