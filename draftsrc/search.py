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

import threading

from whoosh import index, writing, highlight
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser, OrGroup

from gi.repository import GLib

from draftsrc import db
from draftsrc.db import data
from draftsrc import file

INDEX_NAME = 'texts'

schema = Schema(id=ID(unique=True, stored=True),
                title=TEXT(stored=True),
                content=TEXT(analyzer=StemmingAnalyzer(), stored=True),
                tags=KEYWORD(lowercase=True, scorable=True))


def _obtain_group_index_dirname(group_id):
    """Obtain the directory where index is stored for the given group_id"""
    if group_id is None:
        return file.BASE_INDEX_DIR
    with db.connect() as connection:
        group = data.group_for_id(connection, group_id)
        dirname = file.create_index_dir(group['hash_id'], group['parents'])
        return dirname


def create_index_for_group(group_id, in_trash):
    """Create an index of texts contained in given group or its children"""
    with db.connect() as connection:
        dirname = _obtain_group_index_dirname(group_id)
        ix = index.create_in(dirname, schema, INDEX_NAME)
        writer = ix.writer()

        def add_all_texts_in_group(group_id, in_trash=False):

            def add_text(text):
                if text['in_trash'] == in_trash:
                    writer.add_document(id=str(text['id']),
                                        title=text['title'],
                                        tags=' '.join(text['tags']))
                    contents = file.read_from_file(text['hash_id'],
                                                   text['parents'],
                                                   in_trash)
                    if contents:
                        writer.update_document(id=str(text['id']),
                                               content=contents)

            def add_texts_in_group(id):
                for text in data.texts_in_group(connection, id):
                    add_text(text)

                for group in data.groups_in_group(connection, id):
                    add_texts_in_group(group['id'])

            def add_all_texts_in_library():
                for text in data.fetch_texts(connection):
                    add_text(text)

            if group_id is not None:
                add_texts_in_group(group_id)
            else:
                add_all_texts_in_library()

        add_all_texts_in_group(group_id, in_trash)
        writer.commit()

        return ix


class CustomFormatter(highlight.Formatter):
    """Custom formatter for the matched terms."""
    between = '...\n'

    def format_token(self, text, token, replace=False):
        # Use the get_text function to get the text corresponding to the token
        tokentext = highlight.get_text(text, token, replace)

        # Return the text as wrapped around with custom tags
        return "<u>%s</u>" % tokentext


def search_in_group(group_id, search_string, search_tags=False, in_trash=False):
    """Return a dict of text_id:content or text_id:tags in the given group that
    match search_string"""
    ix = None
    try:
        ix = create_index_for_group(group_id, in_trash)
    except index.LockError as e:
        # TODO: (notify) Index locked! Going read-only with existing index.
        dirname = _obtain_group_index_dirname(group_id)
        ix = index.open_dir(dirname, INDEX_NAME, readonly=True, schema=schema)

    if search_tags:
        qp = QueryParser("tags", schema=ix.schema, group=OrGroup)
        query = qp.parse(search_string)

        tag_results = {}
        with ix.searcher() as s:
            results = s.search(query, terms=True)
            for hit in results:
                id = hit['id']
                tag_results[id] = hit.matched_terms()

        return tag_results
    else:
        qp = QueryParser("content", schema=ix.schema)
        query = qp.parse(search_string)

        content_results = {}
        with ix.searcher() as s:
            results = s.search(query, terms=True)
            formatter = CustomFormatter()
            results.formatter = formatter
            for hit in results:
                id = hit['id']
                content_results[id] = hit.highlights("content", top=2)

        return content_results


class ThreadedSearcher():
    _work_data = ()
    busy = False

    def search_in_group_threaded(self, group_id, search_terms, search_tags, in_trash, cb):
        """Creates a new thread and makes it perform search."""
        data_tuple = (group_id, search_terms, search_tags, in_trash, cb)
        self._work_data = data_tuple
        if not self.busy:
            self.activate()

    def activate(self):
        """Set status to active and start working in a seaparate thread."""
        self.busy = True
        thread = threading.Thread(target=self._do_work)
        thread.daemon = True
        thread.start()

    def _do_work(self):
        """Perform searches while there is work data available.
        After search is complete, queues callback on GLib's main loop,
        with obtained results as args."""

        def perform_search(search_group_id, search_terms, search_tags, in_trash):
            """Search for texts matching `search_terms` for the `group_id`."""
            res = search_in_group(search_group_id,
                                  search_terms,
                                  search_tags,
                                  in_trash)
            return res

        results = {}
        post_search_callback = None
        while self._work_data is not None:
            data = self._work_data
            self._work_data = None
            group_id, search_terms, search_tags, in_trash, post_search_callback = data
            results = perform_search(group_id,
                                     search_terms,
                                     search_tags,
                                     in_trash)

        GLib.idle_add(post_search_callback, results)
        self.busy = False


text_finder = ThreadedSearcher()
