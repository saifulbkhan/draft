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
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from gi.repository import GLib, Gio

from notosrc.file import USER_DATA_DIR

DB_URL = os.path.join(USER_DATA_DIR, 'noto.db')


@contextmanager
def connect():
    """Provide a transactional scope around a series of operations.
    Returns a Connection object representing the db"""
    connection = sqlite3.connect(DB_URL)
    connection.isolation_level = None
    try:
        yield connection
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        connection.close()


def init_db():
    """Perform some initial work to set up db and directories for storage"""
    with connect() as connection:
        cursor = connection.cursor()

        # create table for storing keywords
        try:
            create_tag_table = '''
                CREATE TABLE tag (
                    id      INTEGER NOT NULL,
                    keyword VARCHAR,
                    PRIMARY KEY (id)
                )'''
            cursor.execute(create_tag_table)
        except:
            # TODO (notify): tag table exists
            pass

        try:
            # create table for storing text-group metadata
            create_notebook_table = '''
                CREATE TABLE notebook (
                    id            INTEGER NOT NULL,
                    created       VARCHAR,
                    last_modified VARCHAR,
                    name          VARCHAR,
                    parent_id     INTEGER,
                    in_trash      INTEGER,
                    PRIMARY KEY (id),
                    FOREIGN KEY(parent_id) REFERENCES notebook (id)
                )'''
            cursor.execute(create_notebook_table)
        except:
            # TODO (notify): notebook table exists
            pass

        try:
            # create table for storing text metadata
            create_note_table = '''
                CREATE TABLE note (
                    id            INTEGER NOT NULL,
                    created       VARCHAR,
                    last_modified VARCHAR,
                    title         VARCHAR,
                    notebook_id   INTEGER,
                    in_trash      INTEGER,
                    PRIMARY KEY (id),
                    FOREIGN KEY(notebook_id) REFERENCES notebook (id)
                )'''
            cursor.execute(create_note_table)
        except:
            # TODO (notify): note table exists
            pass

        try:
            # create junction table for storing associations between
            # note and tag tables
            create_note_tags_table = '''
                CREATE TABLE note_tags (
                    note_id INTEGER NOT NULL,
                    tag_id  INTEGER NOT NULL,
                    PRIMARY KEY (note_id, tag_id),
                    FOREIGN KEY(note_id) REFERENCES note (id),
                    FOREIGN KEY(tag_id) REFERENCES tag (id)
                )'''
            cursor.execute(create_note_tags_table)
        except:
            # TODO (notify): note_tag table exists
            pass


def get_datetime():
    return datetime.now().isoformat(timespec='milliseconds')


def get_relative_datetime(dt_str):
    date_time =  datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')
    one_day = timedelta(days=1)
    if date_time.date() == datetime.now().date():
        return (_("Today at %s" % date_time.strftime('%I:%M %p')))
    elif date_time.date() == (datetime.now() - one_day).date():
        return (_("Yesterday at %s" % date_time.strftime('%I:%M %p')))

    return date_time.strftime('%d %b %Y')
