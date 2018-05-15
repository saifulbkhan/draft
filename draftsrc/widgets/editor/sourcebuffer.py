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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import re

import gi
gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GtkSource, GLib


class DraftSourceBuffer(GtkSource.Buffer):
    _invis_tag_name = "invisible"
    _link_mark_category = "link"
    _link_marks = {}
    _search_mark = None
    _search_context = None

    _link_regex = r'''\[((?:\[[^^\]]*\]|[^\[\]]|(?=[^\[]*\]))*)\]\([^\)"']*?(\s("[^"]*?"|'[^']*?'))?\)'''
    _link_text_regex = r'''\[((?:\[[^^\]]*\]|[^\[\]]|(?=[^\[]*\]))*)\]'''
    _link_url_regex = r'''\([^\)"']*?(\s("[^"]*?"|'[^']*?'))?\)'''

    _ref_link_regex = r'''\n\s+\[[^\]]*?\](:\s+)(<[^\s<>\(\)\[\]]+>|[^\s\(\)<>\[\]]+)(\s+"[^"]*?"|'[^']*?'|\([^\)]*?\))?(?!\))\s+\n'''
    _ref_link_text_regex = r'''\n\s+\[[^\]]*?\]'''
    _ref_link_url_regex = r'''(:\s+)(<[^\s<>\(\)\[\]]+>|[^\s\(\)<>\[\]]+)(\s+"[^"]*?"|'[^']*?'|\([^\)]*?\))?(?!\))\n'''

    _list_item_regex = '''^( *)([*+-]|\d+\.) [\s\S]+?(?:\n+(?=\1?(?:[-*_] *){3,}(?:\n+|$))|\n{2,}(?! )(?!\1(?:[*+-]|\d+\.) )\n*|\s*$)'''
    _list_bullet_regex = '''^ *(?:[*+-]|\d+\.) +'''

    def __repr__(self):
        return '<DraftSourceBuffer>'

    def __init__(self):
        GtkSource.Buffer.__init__(self)
        self.set_highlight_matching_brackets(False)

        self._search_mark = Gtk.TextMark()
        self.add_mark(self._search_mark, self.get_start_iter())
        self._search_context = GtkSource.SearchContext(buffer=self)
        self._search_context.set_highlight(False)

        search_settings = self._search_context.get_settings()
        search_settings.set_regex_enabled(True)
        search_settings.set_wrap_around(False)

        if not self.get_tag_table().lookup(self._invis_tag_name):
            self.create_tag(self._invis_tag_name, size=0, editable=False)

    def obtain_link_occurences(self):
        start_iter = self.get_start_iter()
        end_iter = self.get_end_iter()
        matches = re.findall(self._link_regex,
                             self.get_text(start_iter, end_iter, True))
        return len(matches)

    def prep_for_search(self):
        self.move_mark(self._search_mark, self.get_start_iter())
        self.remove_source_marks(self.get_start_iter(),
                                 self.get_end_iter(),
                                 self._link_mark_category)
        self._link_marks = {}

    def obtain_link_bounds(self, start, end, backward=False):
        search_settings = self._search_context.get_settings()

        bounds = {}

        search_iter = start
        search_fn = self._search_context.forward2
        if backward:
            search_fn = self._search_context.backward2

        search_settings.set_search_text(str(self._link_text_regex))
        found, text_start, text_end, wrapped = search_fn(search_iter)
        if not found or text_start.compare(end) > 0 or text_end.compare(end) > 0:
            return bounds

        bounds['text'] = [text_start, text_end]

        search_settings.set_search_text(self._link_url_regex)
        found, url_start, url_end, wrapped = search_fn(search_iter)
        if not found or not url_start.equal(text_end):
            return bounds

        bounds['url'] = [url_start, url_end]

        return bounds

    def hide_links(self):
        self.prep_for_search()
        num_occurences = self.obtain_link_occurences()
        for i in range(num_occurences):
            GLib.idle_add(self._hide_next_link)

    def _hide_next_link(self):
        search_settings = self._search_context.get_settings()
        search_settings.set_search_text(str(self._link_regex))

        search_iter = self.get_iter_at_mark(self._search_mark)
        found, start, end, wrapped = self._search_context.forward2(search_iter)
        if found:
            # check if backslash inactivated
            backiter = start.copy()
            backiter.backward_char()
            if self.get_slice(backiter, start, True) == '\\':
                self.move_mark(self._search_mark, end)
                return

            search_iter = start
            search_settings.set_search_text(str(self._link_text_regex))
            found, text_start, text_end, wrapped = self._search_context.forward2(search_iter)
            if found:
                self.apply_tag_by_name(self._invis_tag_name, text_end, end)

            start_mark = self.create_source_mark(None,
                                                 self._link_mark_category,
                                                 start)
            end_mark = self.create_source_mark(None,
                                               self._link_mark_category,
                                               end)
            self._link_marks[start_mark] = end_mark
            self.move_mark(self._search_mark, end)

    def update_links(self):
        it = self.get_start_iter()
        while self.forward_iter_to_source_mark(it, self._link_mark_category):
            start = it.copy()
            if self.forward_iter_to_source_mark(it, self._link_mark_category):
                end = it.copy()
                start_mark = self.get_source_marks_at_iter(start, self._link_mark_category)[0]
                end_mark = self.get_source_marks_at_iter(end, self._link_mark_category)[0]
                if not self._link_marks.get(start_mark) == end_mark:
                    self.remove_tag_by_name(self._invis_tag_name, start, end)
                else:
                    bounds = self.obtain_link_bounds(start, end)
                    if not bounds.get('text') or not bounds.get('url'):
                        self.remove_tag_by_name(self._invis_tag_name, start, end)
                    else:
                        # check if backslash inactivated
                        # move forward (left gravity source mark)
                        backiter = start.copy()
                        backiter.forward_char()
                        if self.get_slice(backiter, start, True) == '\\':
                            self.remove_tag_by_name(self._invis_tag_name, start, end)

        self.hide_links()

    def cursor_is_on_link(self):
        insert_mark = self.get_insert()
        insert = self.get_iter_at_mark(insert_mark)

        for source_mark in self._link_marks:
            start = self.get_iter_at_mark(source_mark)
            end = self.get_iter_at_mark(self._link_marks[source_mark])
            if insert.compare(start) > 0 and insert.compare(end) < 0:
                # check if is an image link
                backiter = start.copy()
                backiter.backward_char()
                if self.get_slice(backiter, start, True) == '!':
                    return True, True, start, end
                else:
                    return True, False, start, end

        return False, False, None, None

    def get_word_at_iter(self, textiter):
        start = None
        end = None
        if textiter.starts_word():
            start = textiter
            end = textiter.copy()
            end.forward_word_end()
        elif textiter.ends_word():
            start = textiter.copy()
            start.backward_word_start()
            end = textiter
        elif textiter.inside_word():
            start = textiter.copy()
            end = textiter.copy()
            start.backward_word_start()
            end.forward_word_end()

        if start and end:
            word = self.get_slice(start, end, True)
            return word, start, end

        return None, start, end

    def replace_text_between(self, start, end, new_text):
        self.delete(start, end)
        self.insert(start, new_text)

    def is_on_empty_line(self, textiter):
        return textiter.starts_line() and textiter.ends_line()

    def is_on_list_item(self, textiter):
        start = textiter.copy()
        end = textiter.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        # assuming iterator is not on a line outside buffer bounds.
        start.backward_line()

        item_regex = re.compile(self._list_item_regex)
        bullet_regex = re.compile(self._list_bullet_regex)

        item = self.get_slice(start, end, True)
        match = item_regex.match(item)
        if match is not None:
            bullet_match = bullet_regex.match(item)
            if bullet_match is not None:
                return True, (bullet_match.end() - bullet_match.start())

        return False, -1
