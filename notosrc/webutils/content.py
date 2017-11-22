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

from notosrc.defs import DATA_DIR

NOTO_DIR = 'file://' + os.path.join(DATA_DIR, 'noto')

head_string = '''
<head>
    <script type="text/x-mathjax-config">
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
        src="%s/mathjax/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
    </script>
</head>
''' % (NOTO_DIR)

body_string = '''
<body>
%s
</body>
'''

html_string = head_string + body_string
