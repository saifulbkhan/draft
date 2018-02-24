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
import threading
from contextlib import contextmanager
from datetime import datetime
from collections import OrderedDict

from gi.repository import GLib, Gio

from notosrc.file import USER_DATA_DIR, make_backup
from notosrc.db.migrations import migrate_db

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


def version():
    """Returns the current db version (stored in user_version pragma)"""
    with connect() as conn:
        cursor = conn.cursor()
        res = cursor.execute('PRAGMA user_version')
        return res.fetchone()[0]


def is_new():
    """Returns True if db has no tables otherwise False"""
    with connect() as conn:
        cursor = conn.cursor()
        res = cursor.execute('''
            SELECT count(*) FROM sqlite_master WHERE type = "table"
        ''')
        return res.fetchone()[0] == 0


def init_db(app_version):
    """Perform some initial work to set up db for use with the current
    application version"""
    # if existing db, then migration needed
    if not is_new():
        with make_backup(DB_URL):
            migrate_db(app_version)
            return
    else:
        with connect() as connection:
            cursor = connection.cursor()

            # create table for storing keywords
            try:
                create_tag_table = '''
                    CREATE TABLE tag (
                        keyword TEXT NOT NULL DEFAULT NULL PRIMARY KEY,
                    )'''
                cursor.execute(create_tag_table)
            except:
                # TODO (notify): something went wrong
                pass

            try:
                # create table for storing text-group metadata
                create_group_table = '''
                    CREATE TABLE 'group' (
                        id            TEXT    NOT NULL DEFAULT NULL PRIMARY KEY,
                        name          TEXT    NOT NULL DEFAULT NULL,
                        created       TEXT    NOT NULL DEFAULT NULL,
                        last_modified TEXT    NOT NULL DEFAULT NULL,
                        parent_id     INTEGER          DEFAULT NULL REFERENCES 'group' (id),
                        in_trash      INTEGER NOT NULL DEFAULT 0
                    )'''
                cursor.execute(create_group_table)
            except:
                # TODO (notify): something went wrong
                pass

            try:
                # create table for storing text metadata
                create_text_table = '''
                    CREATE TABLE text (
                        id                 TEXT    NOT NULL DEFAULT NULL PRIMARY KEY,
                        title              TEXT    NOT NULL DEFAULT NULL,
                        created            TEXT    NOT NULL DEFAULT NULL,
                        last_modified      TEXT    NOT NULL DEFAULT NULL,
                        parent_id          INTEGER          DEFAULT NULL REFERENCES 'group' (id),
                        in_trash           INTEGER NOT NULL DEFAULT 0,
                        markup             TEXT             DEFAULT NULL,
                        subtitle           TEXT             DEFAULT NULL,
                        word_goal          INTEGER          DEFAULT NULL,
                        last_edit_position INTEGER          DEFAULT NULL
                    )'''
                cursor.execute(create_text_table)
            except:
                # TODO (notify): something went wrong
                pass

            try:
                # create junction table for storing associations between
                # text and tag tables
                create_text_tags_table = '''
                    CREATE TABLE text_tags (
                        text_id     INTEGER NOT NULL DEFAULT NULL REFERENCES text (id),
                        tag_keyword TEXT    NOT NULL DEFAULT NULL REFERENCES tag (keyword),
                        UNIQUE (text_id, tag_keyword)
                    )'''
                cursor.execute(create_text_tags_table)
            except:
                # TODO (notify): something went wrong
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


class RequestQueue(OrderedDict):
    """A dict with queue like FIFO methods"""
    active = False
    execution_fn = None

    def __init__(self, immediate_activation=True):
        super().__init__()
        self.immediate_activation = immediate_activation

    def enqueue(self, key, val):
        """Put an item in queue with a unique key. If the queue was empty and
        should immeadiately be working on the requests, activate it."""
        self[key] = val
        if not self.active and self.immediate_activation:
            self.activate()

    def activate(self):
        """Work on the contents of the queue, in a separate thread."""
        self.active = True
        thread = threading.Thread(target=self.do_work)
        thread.daemon = True
        thread.start()

    def dequeue(self):
        """Get the oldest item inserted into the queue."""
        key, val = None, None
        if len(self):
            key, val = self.popitem(last=False)

        return key, val

    def do_work(self):
        """Loop over the queue and for each item perform `execution_fn`
        operation."""
        if self.execution_fn is None:
            return

        while True:
            id, values = self.dequeue()
            if not (id and values):
                break

            with connect() as connection:
                self.execution_fn(connection, id, values)

        self.active = False


# a queue for regular updates that need to be performed immediately
async_updater = RequestQueue()

# TODO: a queue for updates which could be issued periodically
timed_updater = RequestQueue()
time_period = 180

# a queue of updates that will be executed when the app quits
final_updater = RequestQueue(immediate_activation=False)
