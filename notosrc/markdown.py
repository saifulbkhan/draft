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
import re, os.path

from gi.repository import GLib

from notosrc.utils.mistune import escape
from notosrc.utils.mistune import Markdown, InlineLexer, BlockLexer, Renderer
from notosrc.defs import DATA_DIR

NOTO_DIR = 'file://' + os.path.join(DATA_DIR, 'noto')

html_string = '''
<head>
    <script type="text/x-mathjax-config">
      MathJax.Hub.Config({
        tex2jax: {
          inlineMath: [ ['$','$'] ],
          processEscapes: true,
          imageFont: null
        },
        showMathMenu: false
      });
    </script>
    <script type="text/javascript"
        src="%s/mathjax/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
    </script>
</head>
<body>
%s
</body>
'''

class MathBlockLexer(BlockLexer):
    def __init__(self):
        super(MathBlockLexer, self).__init__()
        self.enable_math()

    def enable_math(self):
        self.rules.block_math = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
        self.default_rules.extend(['block_math'])

    def parse_block_math(self, m):
        """Parse a $$math$$ block"""
        self.tokens.append({
            'type': 'block_math',
            'text': m.group(1)
        })

class MathInlineLexer(InlineLexer):
    def __init__(self, renderer):
        super(MathInlineLexer, self).__init__(renderer)
        self.enable_math()

    def enable_math(self):
        self.rules.math = re.compile(r'\$(.+?)(?<!\$)\$(?!\$)')
        self.default_rules.insert(0, 'math')
        self.rules.text = re.compile(
            r'^[\s\S]+?(?=[\\<!\[_*`~\$]|https?://| {2,}\n|$)'
        )

    def output_math(self, m):
        return self.renderer.math(m.group(1))


class CustomRenderer(Renderer):
    def block_math(self, text):
        return '$$%s$$' % text

    def math(self, text):
        return '$%s$' % text

    def block_code(self, text, lang):
        inlinestyles = self.options.get('inlinestyles', False)
        linenos = self.options.get('linenos', False)
        code = format_code(text, lang, inlinestyles, linenos)
        return code


class CustomMarkdown(Markdown):
    def output_block_math(self):
        return self.renderer.block_math(self.token['text'])


def format_code(text, lang, inlinestyles=False, linenos=False):
    if not lang:
        lang = "text"

    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import html

        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = html.HtmlFormatter(
            noclasses=inlinestyles, linenos=linenos
        )
        code = highlight(text, lexer, formatter)
        if linenos:
            return '<div class="highlight-wrapper">%s</div>\n' % code
        return code
    except Exception as e:
        # Maybe a warning message needed here
        text = text.strip()
        return '\n<pre><code>%s</code></pre>\n' % escape(text)

def render_markdown(text, webview):
    renderer = CustomRenderer(hard_wrap=True)
    inline_renderer = MathInlineLexer(renderer)
    block_renderer = MathBlockLexer()

    markdown = CustomMarkdown(renderer, inline_renderer, block_renderer)
    content = markdown(text)
    webview.set_editable(True)
    content = html_string % (NOTO_DIR, content)
    GLib.idle_add(webview.load_html, content, NOTO_DIR)
