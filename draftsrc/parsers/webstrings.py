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

meta_string = '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'

title_string = '<title>%s</title>'

mathjax_local_src = os.path.join(DRAFT_DIR, 'mathjax', 'MathJax.js')
mathjax_remote_src = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.4/MathJax.js"
mathjax_config = "?config=TeX-AMS-MML_HTMLorMML"

script_string = '''<script type="text/x-mathjax-config">
    MathJax.Hub.Config({
    tex2jax: {
        inlineMath: [ ['$','$'] ],
        processEscapes: true,
        imageFont: null
    },
    showMathMenu: false,
    "HTML-CSS": { scale: 75, linebreaks: { automatic: true } }
    });
</script>
<script type="text/javascript"
    src="%s">
</script>'''

mathjax_script_string = script_string % (mathjax_local_src + mathjax_config)
export_mathjax_script_string = script_string % (mathjax_remote_src + mathjax_config)

head_string = '''
<head>
%s
%s
</head>
''' % (meta_string, mathjax_script_string)

export_head_string = '''
<head>
%s
%s
%s
</head>
''' % (meta_string, title_string, export_mathjax_script_string)

body_string = '<body>\n%s</body>'

html_string = head_string + body_string
export_html_string = export_head_string + body_string
