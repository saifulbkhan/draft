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

import os.path

from draftsrc.defs import DATA_DIR

DRAFT_DIR = 'file://' + os.path.join(DATA_DIR, 'draft')

meta_string = '<meta charset="UTF-8">'

title_string = '<title>%s</title>'

katex_style_local_src = os.path.join(DRAFT_DIR,
                                     'katex',
                                     'katex.min.css')
katex_style_remote_src = 'https://cdn.jsdelivr.net/npm/katex@0.10.0-alpha/dist/katex.min.css'
katex_local_src = os.path.join(DRAFT_DIR,
                               'katex',
                               'katex.min.js')
katex_remote_src = 'https://cdn.jsdelivr.net/npm/katex@0.10.0-alpha/dist/katex.min.js'
auto_render_local_src = os.path.join(DRAFT_DIR,
                                     'katex',
                                     'contrib',
                                     'auto-render.min.js')
auto_render_remote_src = 'https://cdn.jsdelivr.net/npm/katex@0.10.0-alpha/dist/contrib/auto-render.min.js'

script_string = '''<link rel="stylesheet" href="%s">
<script src="%s" type="text/javascript"></script>
<script src="%s" type="text/javascript"></script>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(
      document.body,
      {
        delimiters: [
          {left: "$$", right: "$$", display: true},
          {left: "$", right: "$", display: false}
        ]
      }
    );
  });
</script>'''

katex_script_string = script_string % (katex_style_local_src,
                                       katex_local_src,
                                       auto_render_local_src)
export_katex_script_string = script_string % (katex_style_remote_src,
                                              katex_remote_src,
                                              auto_render_remote_src)

style_string = '''<style type="text/css">%s</style>'''

head_string = '''
<head>
%s
%s
</head>
''' % (meta_string, katex_script_string)

export_head_string = '''
<head>
%s
%s
%s
</head>
''' % (meta_string, title_string, export_katex_script_string)

export_styled_head_string = '''
<head>
%s
%s
%s
%s
</head>
''' % (meta_string, title_string, export_katex_script_string, style_string)

body_string = '<body>\n%s</body>'

html_wrapper = '<!DOCTYPE html>\n<html>%s\n</html>'

html_string = html_wrapper % (head_string + body_string)
export_html_string = html_wrapper % (export_head_string + body_string)
export_styled_html_string = html_wrapper % (export_styled_head_string + body_string)
