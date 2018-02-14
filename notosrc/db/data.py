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

from hashlib import sha256

from notosrc import db


def create_keyword(conn, keyword):
    """Create a new keyword"""
    query = '''
        INSERT INTO tag (keyword)
             VALUES (:keyword)'''
    cursor = conn.cursor()
    cursor.execute(query, {'keyword': keyword})


def create_text(conn, name, group_id=None):
    """Create a new text document and return its id"""
    datetime = db.get_datetime()
    query = '''
        INSERT INTO text (created, last_modified, title, parent_id, in_trash)
             VALUES (:created, :modified, :title, :parent_id, :in_trash)'''
    cursor = conn.cursor()
    cursor.execute(query, {"created": datetime,
                           "modified": datetime,
                           "title": name,
                           "parent_id": group_id,
                           "in_trash": 0})

    return get_last_insert_id(conn)


def create_group(conn, name, group_id=None):
    """Create a new text group and return its id"""
    datetime = db.get_datetime()
    query = '''
        INSERT INTO group (created, last_modified, name, parent_id, in_trash)
             VALUES (:created, :modified, :name, :parent_id, :in_trash)'''
    cursor = conn.cursor()
    cursor.execute(query, {"created": datetime,
                           "modified": datetime,
                           "name": name,
                           "parent_id": group_id,
                           "in_trash": 0})

    return get_last_insert_id(conn)


def get_last_insert_id(conn):
    """Returns the rowid of the last row that was inserted through the active
    connection"""
    # premature commit to ensure we get proper id
    conn.commit()

    id_query = 'SELECT last_insert_rowid()'
    cursor = conn.cursor()
    res = cursor.execute(id_query)
    return res.fetchone()[0]


def update_text(conn, text_id, values):
    """Update the values for given text id"""
    query = '''
        UPDATE text
           SET last_modified = :modified
             , title = :title
             , parent_id = :parent_id
             , in_trash = :in_trash
         WHERE id = :id'''
    cursor = conn.cursor()
    cursor.execute(query, {"modified": values['last_modified'],
                           "title": values['title'],
                           "parent_id": values['parent_id'],
                           "in_trash": values['in_trash'],
                           "id": text_id})

    update_keywords_for_text(conn, text_id, values['keywords'])


def update_keywords_for_text(conn, text_id, keywords):
    """Update the keywords on given text"""
    values = []
    for k in keywords:
        keyword = fetch_keyword(conn, k)
        values.append({"text_id": text_id, "tag_keyword": keyword})

    cursor = conn.cursor()

    # remove old keywords if any
    delete_query = '''
        DELETE FROM text_tags
              WHERE text_id = :id'''
    cursor.execute(delete_query, {"id": text_id})

    # add new keywords if any
    insert_query = '''
        INSERT INTO text_tags (text_id, tag_keyword)
             VALUES (:text_id, :tag_keyword)'''
    cursor.executemany(insert_query, values)


def update_group(conn, group_id, values):
    """Update the values for given group id"""
    update_query = '''
        UPDATE group
           SET last_modified = :modified
             , name = :name
             , parent_id = :parent_id
             , in_trash = :in_trash
         WHERE id = :group_id'''
    cursor = conn.cursor()
    cursor.execute(update_query, {"modified": values['last_modified'],
                                  "name": values['name'],
                                  "parent_id": values['parent_id'],
                                  "in_trash": values['in_trash'],
                                  "group_id": group_id})

    # trash items in group, if the group is being trashed
    if values['in_trash']:

        # recursive function that sets `in_trash` to true
        # for given group, its subgroups and texts.
        def _trash_groups_and_texts(conn, group):
            trash_group_query = '''
                UPDATE group
                   SET in_trash = 1
                 WHERE id = :id'''
            cursor.execute(trash_group_query, {"id": group})

            trash_texts_query = '''
                UPDATE text
                   SET in_trash = 1
                 WHERE parent_id = :id'''
            cursor.execute(trash_texts_query, {"id": group})

            select_subgroups_query = '''
                SELECT id
                  FROM group
                 WHERE parent_id = :id'''
            for subgroup in cursor.execute(select_subgroups_query, {"id": group}):
                _trash_groups_and_texts(conn, subgroup[0])

        _trash_groups_and_texts(conn, group_id)


def delete_text(conn, text_id):
    """Delete a text document from db"""
    query = '''
        DELETE FROM text
              WHERE id = :id'''
    cursor = conn.cursor()
    cursor.execute(query, {"id": text_id})


def delete_group(conn, group_id):
    """Delete a text group from db"""
    query = '''
        DELETE FROM group
              WHERE id = :id'''
    cursor = conn.cursor()
    cursor.execute(query, {"id": group_id})

    # delete texts belonging to group from the db
    delete_texts_query = '''
        DELETE FROM text
              WHERE parent_id = :id'''
    cursor.execute(delete_texts_query, {"id": group_id})

    select_query = '''
        SELECT id
          FROM group
         WHERE parent_id = :id'''
    for row in cursor.execute(query, {"id": group_id}):
        delete_group(conn, row[0])


def delete_orphan_tags(conn):
    """Delete keywords not associated with  any text"""
    orphan_tags_query = '''
        DELETE FROM tag
              WHERE keyword NOT IN (SELECT tag_keyword
                                      FROM text_tags)'''
    cursor = conn.cursor()
    cursor.execute(orphan_tags_query)


def fetch_keyword(conn, keyword):
    """Fetch equivalent of the given keyword if exists, create new otherwise"""
    # TODO: support case-insensitive matching for Unicode characters in keyword.
    # sqlite `LIKE` operator only does case-insensitive matching for ASCII
    # characters. To do case-insensitive matching for Unicode as well, maybe
    # use ICU plugin for sqlite or filter another way.
    query = '''
        SELECT keyword
          FROM tag
         WHERE keyword LIKE :keyword'''
    cursor = conn.cursor()
    cursor.execute(query, {"keyword": keyword})

    res = cursor.fetchone()
    if res:
        return res[0]

    create_keyword(conn, keyword)
    return keyword


def fetch_keywords_for_text(conn, text_id):
    """Return a list of keywords tagged to given text"""
    query = '''
        SELECT tag_keyword
          FROM text_tags
         WHERE text_id = :id'''
    cursor = conn.cursor()
    keywords = [k[0] for k in cursor.execute(query, {"id": text_id})]
    return keywords


def fetch_parents_for_text(conn, text_id):
    """Returns a list of hash strings for parent groups that joined
    together can form a relative path to text dir"""
    query = '''
        SELECT %s
          FROM %s
         WHERE id = :id'''

    cursor = conn.cursor()
    res = cursor.execute(query % ('parent_id', 'text'), {"id": text_id})

    parents = []
    parent = res.fetchone()[0]
    while parent:
        parents.append(sha256(('notebook%s' % parent).encode()).hexdigest())
        res = cursor.execute(query % ('parent_id', 'group'), {"id": parent})
        parent = res.fetchone()[0]

    parents.reverse()
    return parents


def fetch_texts(conn, where='', order='', args={}):
    """Return an iterator of texts from the db, satisfying optional
    constraints"""
    query = '''
        SELECT id
             , title
             , created
             , last_modified
             , parent_id
             , in_trash
          FROM text'''
    if where:
        query += '\nWHERE %s' % where
    if order:
        query += '\nORDER BY %s' % order

    cursor = conn.cursor()
    for row in cursor.execute(query, args):
        values = {
            'id': row[0],
            'title': row[1],
            'created': row[2],
            'last_modified': row[3],
            'parent_id': row[4],
            'in_trash': row[5]
        }

        # create hash_id for text
        values['hash_id'] = sha256(('note%s' % values['id']).encode()).hexdigest()

        # create a list of parents
        values['parents'] = fetch_parents_for_text(conn, values['id'])

        # obtain a list of keywords
        values['keywords'] = fetch_keywords_for_text(conn, values['id'])

        yield values


def texts_not_in_groups(conn):
    """Return an iterator of texts from the db, which have no parent group"""
    where_condition = 'parent_id IS NULL'
    return fetch_texts(conn, where_condition)


def text_in_group(conn, group_id):
    """Return an iterator of texts from the db, with given parent group"""
    where_condition = 'parent_id = :id'
    args = {"id": group_id}
    return fetch_texts(conn, where_condition, args=args)


def text_for_id(conn, text_id):
    """Return the text for given db id"""
    where_condition = 'id = :id'
    args = {"id": text_id}
    gen = fetch_texts(conn, where_condition, args=args)
    return next(gen)


def fetch_groups(conn, where='', order='', args={}):
    """Return an iterator of text groups from the db, satisfying optional
    constraints"""
    query = '''
        SELECT id
             , name
             , created
             , last_modified
             , parent_id
             , in_trash
          FROM group'''
    if where:
        query += '\nWHERE %s' % where
    if order:
        query += '\nORDER BY %s' % order

    cursor = conn.cursor()
    for row in cursor.execute(query, args):
        values = {
            'id': row[0],
            'name': row[1],
            'created': row[2],
            'last_modified': row[3],
            'parent_id': row[4],
            'in_trash': row[5]
        }
        yield values


def groups_not_in_groups(conn):
    """Return an iterator of groups from the db, which have no parent group"""
    where_condition = 'parent_id IS NULL'
    return fetch_groups(conn, where_condition)


def groups_in_group(conn, group_id):
    """Return an iterator of groups from the db, with given parent group"""
    where_condition = 'parent_id is :id'
    args = {"id": group_id}
    return fetch_groups(conn, where_condition, args=args)
