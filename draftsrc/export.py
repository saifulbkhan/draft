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

from os import path
from gettext import gettext as _

from gi.repository import Gtk, GLib, Gio

from draftsrc import file
from draftsrc import db
from draftsrc.db import data
from draftsrc.parsers import markup
from draftsrc.parsers.webstrings import export_html_string
from draftsrc.parsers.webstrings import export_styled_html_string
from draftsrc.defs import DATA_DIR

DRAFT_DIR = path.join(DATA_DIR, 'draft')

main_window = None


def handle_html_export_request(html_contents, suggested_export_title=""):
    """Brings up a GtkDialog transient to the main window and allows the user
    to set export options."""
    builder = Gtk.Builder()
    builder.add_from_resource('/org/gnome/Draft/export.ui')

    html_export_dialog = builder.get_object('html_export_dialog')
    html_export_dialog.set_transient_for(main_window)

    html_dialog_header = builder.get_object('html_dialog_header')
    html_title_entry = builder.get_object('html_title_entry')
    html_export_chooser = builder.get_object('html_export_chooser')
    html_export_check = builder.get_object('html_export_check')
    html_cancel_button = builder.get_object('html_cancel_button')
    html_save_button = builder.get_object('html_save_button')

    if len(html_contents) > 1:
        html_dialog_header.set_subtitle(_("%s Texts") % len(html_contents))

    default_path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    html_export_chooser.set_current_folder(default_path)

    html_title_entry.set_text(suggested_export_title)

    def _on_cancel_clicked(widget):
        html_export_dialog.emit('response', Gtk.ResponseType.CANCEL)

    def _on_save_clicked(widget):
        html_export_dialog.emit('response', Gtk.ResponseType.ACCEPT)

    html_cancel_button.connect('clicked', _on_cancel_clicked)
    html_save_button.connect('clicked', _on_save_clicked)

    response = html_export_dialog.run()
    if response == Gtk.ResponseType.ACCEPT:
        title = html_title_entry.get_text()
        destination_folder = html_export_chooser.get_current_folder()
        html_body = ''.join(html_contents)
        with_style = html_export_check.get_active()
        save_html(destination_folder,
                  title,
                  html_body,
                  with_style=with_style)

    html_export_dialog.destroy()


def save_html(parent, title, body, with_style=False):
    """Save html body along with up proper title (and optionally style) to the
    given parent folder."""
    html = ""
    if with_style:
        settings = Gio.Settings.new('org.gnome.Draft')
        stylesheet = settings.get_string('stylesheet')
        css_path = path.join(DRAFT_DIR, 'styles', stylesheet)
        with open(css_path, 'r') as f:
            css = f.read()
            html = export_styled_html_string % (title, css, body)
    else:
        html = export_html_string % (title, body)

    filename = '-'.join(title.lower().split())
    fpath = path.join(parent, filename)
    with open(fpath, 'w') as f:
        f.write(html)


def request_save_html_for_files(files, suggested_export_title=""):
    """Expects a dict of filenames mapped to their parent group names' list.
    Reads these files, converts the markup to html, and then saves them, if
    user permits through the final dialog."""
    html_contents = []
    for filename in files:
        content = file.read_from_file(filename, files[filename])
        html_contents.append(markup.render_markdown(content))
    handle_html_export_request(html_contents, suggested_export_title)


def request_save_html_for_group(group):
    """Saves all texts within a group as appended html content. The group while
    exporting is flattened, i.e. all texts within subgroups are appended one
    after another, treated as belonging to one single group."""
    group_id = group['id']
    texts_in_group = {}
    with db.connect() as connection:

        def append_texts_in_group(id):
            texts = data.texts_in_group(connection, id)
            if id is None:
                texts = data.texts_not_in_groups(connection)
            for text in texts:
                if text['in_trash'] == False:
                    texts_in_group[text['hash_id']] = text['parents']
            for group in data.groups_in_group(connection, id):
                append_texts_in_group(group['id'])

        append_texts_in_group(group_id)

    request_save_html_for_files(texts_in_group, group['name'])
