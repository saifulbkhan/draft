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

from notosrc import db

# A dict for storing db versions corresponding to the application version they
# were meant to be used with; this should be updated every new realease.
db_versions = {
    '0.1.0': 1,
}

# The 'up' script, for a version X, allows migration from version X to the next
# version Y. The 'down' script, for a version X, allows migration from the next
# version Y, to version X
migration_scripts = {
    0: {
        'up': '''
            /* update note_tags table */
            CREATE TABLE text_tags (
                text_id     INTEGER NOT NULL DEFAULT NULL REFERENCES text (id),
                tag_keyword TEXT    NOT NULL DEFAULT NULL REFERENCES tag (keyword),
                UNIQUE (text_id, tag_keyword)
            );

            INSERT INTO text_tags (text_id, tag_keyword)
                 SELECT note_id,
                        (SELECT keyword
                           FROM tag
                          WHERE id = tag_id)
                   FROM note_tags;

            DROP TABLE note_tags;

            /* update table `tag` */
            CREATE TABLE tag2 (
                keyword TEXT NOT NULL DEFAULT NULL PRIMARY KEY
            );

            INSERT INTO tag2 (keyword)
                 SELECT keyword
                   FROM tag;

            DROP TABLE tag;

            ALTER TABLE tag2
              RENAME TO tag;

            /* update table `notebook` */
            CREATE TABLE 'group' (
                id            TEXT    NOT NULL DEFAULT NULL PRIMARY KEY,
                name          TEXT    NOT NULL DEFAULT NULL,
                created       TEXT    NOT NULL DEFAULT NULL,
                last_modified TEXT    NOT NULL DEFAULT NULL,
                parent_id     INTEGER          DEFAULT NULL REFERENCES 'group' (id),
                in_trash      INTEGER NOT NULL DEFAULT 0
            );

            INSERT INTO 'group' (id, name, created, last_modified, parent_id, in_trash)
                 SELECT id, name, created, last_modified, parent_id, in_trash
                   FROM notebook;

            DROP TABLE notebook;

            /* update table `note` */
            CREATE TABLE text (
                id                 INTEGER NOT NULL PRIMARY KEY,
                title              TEXT    NOT NULL DEFAULT NULL,
                created            TEXT    NOT NULL DEFAULT NULL,
                last_modified      TEXT    NOT NULL DEFAULT NULL,
                parent_id          INTEGER          DEFAULT NULL REFERENCES 'group' (id),
                in_trash           INTEGER NOT NULL DEFAULT 0,
                markup             TEXT             DEFAULT NULL,
                subtitle           TEXT             DEFAULT NULL,
                word_goal          TEXT             DEFAULT NULL,
                last_edit_position TEXT             DEFAULT NULL
            );

            INSERT INTO text (id, title, created, last_modified, parent_id, in_trash)
                 SELECT id, title, created, last_modified, notebook_id, in_trash
                   FROM note;

            DROP TABLE note;

            /* set version */
            PRAGMA user_version = 1;
            ''',

        'down': '''
            /* downgrade table `tag` */
            CREATE TABLE tag2 (
                id      INTEGER NOT NULL PRIMARY KEY,
                keyword TEXT             DEFAULT NULL
            );

            INSERT INTO tag2 (keyword)
                 SELECT keyword
                   FROM tag;

            DROP TABLE tag;

            ALTER TABLE tag2
              RENAME TO tag;

            /* downgrade table `group` */
            CREATE TABLE notebook (
                id            INTEGER NOT NULL,
                created       TEXT,
                last_modified TEXT,
                name          TEXT,
                parent_id     INTEGER,
                in_trash      INTEGER,
                PRIMARY KEY (id),
                FOREIGN KEY(parent_id) REFERENCES notebook (id)
            );

            INSERT INTO 'group' (id, name, created, last_modified, parent_id, in_trash)
                 SELECT id, name, created, last_modified, parent_id, in_trash
                   FROM notebook;

            DROP TABLE 'group';

            /* downgrade table `text` */
            CREATE TABLE note (
                id            INTEGER NOT NULL PRIMARY KEY,
                title         TEXT    NOT NULL DEFAULT NULL,
                created       TEXT    NOT NULL DEFAULT NULL,
                last_modified TEXT    NOT NULL DEFAULT NULL,
                notebook_id   INTEGER          DEFAULT NULL REFERENCES notebook (id),
                in_trash      INTEGER NOT NULL
            );

            INSERT INTO note (id, title, created, last_modified, notebook_id, in_trash)
                 SELECT id, title, created, last_modified, parent_id, in_trash
                   FROM text;

            DROP TABLE text;

            /* downgrade table `text_tags` */
            CREATE TABLE note_tags (
                note_id INTEGER NOT NULL DEFAULT NULL REFERENCES note (id),
                tag_id  TEXT    NOT NULL DEFAULT NULL REFERENCES tag (id),
                UNIQUE (note_id, tag_id)
            );

            INSERT INTO note_tags (note_id, tag_id)
                 SELECT text_id,
                        (SELECT id
                           FROM tag
                          WHERE keyword = tag_keyword)
                   FROM text_tags;

            DROP TABLE text_tags;

            /* set version */
            PRAGMA user_version = 0;
            '''
    }
}


# TODO: Save a copy of the current db maybe when downgrading? This might help
# restore user data if they wish to return to the newer version, since the older
# scripts will not be able to convert from later versions of the db. A smarter
# way would be to do the initial up/downgrading through a webservice which uses
# a script that understands all the different db versions.


# Only upgrades will reliably work at the moment!
def migrate_db(desired_version):
    """Updates db scehma to match the version that can be used by
    @desired_version of the application; arg value is the version of the
    application, not db version."""
    desired_db_version = db_versions[desired_version]
    current_db_version = db.version()

    # default action is to upgrade scehma
    action = 'up'
    key_offset = 0
    if desired_db_version < current_db_version:
        action = 'down'
        key_offset = 1

    while current_db_version != desired_db_version:
        # the correct key for migration_scripts
        scriptkey = current_db_version - key_offset
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.executescript(migration_scripts[scriptkey][action])

        current_db_version = db.version()
        # TODO (notify): db migration step successful
