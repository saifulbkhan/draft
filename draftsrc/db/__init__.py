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
from datetime import datetime, timedelta

from draftsrc.file import USER_DATA_DIR, make_backup
from draftsrc.db import data
from draftsrc.db import requestqueue
from draftsrc.db.migrations import migrate_db

DB_URL = os.path.join(USER_DATA_DIR, 'draft.db')


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
                        keyword TEXT NOT NULL DEFAULT NULL PRIMARY KEY
                    )'''
                cursor.execute(create_tag_table)
            except:
                # TODO (notify): something went wrong
                pass

            try:
                # create table for storing text-group metadata
                create_group_table = '''
                    CREATE TABLE 'group' (
                        id            INTEGER NOT NULL DEFAULT NULL PRIMARY KEY,
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
                        id                 INTEGER NOT NULL DEFAULT NULL PRIMARY KEY,
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


def get_datetime_last_n_days(last_n_days):
    dt = datetime.now() - timedelta(days=last_n_days)
    return dt.isoformat(timespec='milliseconds')


def get_relative_datetime(dt_str):
    date_time =  datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')
    one_day = timedelta(days=1)
    if date_time.date() == datetime.now().date():
        return (_("Today at %s" % date_time.strftime('%I:%M %p')))
    elif date_time.date() == (datetime.now() - one_day).date():
        return (_("Yesterday at %s" % date_time.strftime('%I:%M %p')))

    return date_time.strftime('%d %b %Y')


def get_datetime_from_string(dt_str):
    return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')


# a queue for regular updates that need to be performed immediately
async_text_updater = requestqueue.UpdateRequestQueue()
async_text_updater.execution_fn = data.update_text
async_text_updater.fetch_fn = data.text_for_id

# a queue for asynchrnously deleting texts immediately
async_text_deleter = requestqueue.DeleteRequestQueue()
async_text_deleter.deletion_fn = data.delete_text

# a queue for asynchrnously deleting texts immediately
async_group_deleter = requestqueue.DeleteRequestQueue()
async_group_deleter.deletion_fn = data.delete_group

# TODO: a queue for updates which could be issued periodically
timed_updater = requestqueue.UpdateRequestQueue()
time_period = 180

# a queue of updates that will be executed when the app quits
final_text_updater = requestqueue.UpdateRequestQueue(async=False,
                                                     immediate_activation=False)
final_text_updater.execution_fn = data.update_text
final_text_updater.fetch_fn = data.text_for_id
