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

from draftsrc.parsers.webstrings import export_html_string
from draftsrc.parsers.webstrings import export_styled_html_string
from draftsrc.defs import DATA_DIR

DRAFT_DIR = path.join(DATA_DIR, 'draft')


def save_html(parent, title, body, with_style=False):
    html = ""
    if with_style:
        css_path = path.join(DRAFT_DIR, 'styles', 'webview.css')
        with open(css_path, 'r') as f:
            css = f.read()
            html = export_styled_html_string % (title, css, body)
    else:
        html = export_html_string % (title, body)

    filename = '-'.join(title.lower().split())
    fpath = path.join(parent, filename)
    with open(fpath, 'w') as f:
        f.write(html)
