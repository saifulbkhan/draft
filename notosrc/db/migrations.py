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
    '0.1.0': 0,
}

# The 'up' script, for a version X, allows migration from version X to the next
# version Y. The 'down' script, for a version X, allows migration from the next
# version Y, to version X
migration_scripts = {
    0: {
        'up': '',
        'down': ''
    }
}


def get_db_version():
    """Returns the current db version (stored in user_version pragma)"""
    with db.connect() as conn:
        cursor = conn.cursor()
        res = cursor.execute('PRAGMA user_version')
        return res.fetchone()[0]


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
    current_db_version = get_db_version()

    # if new db, then no migration needed
    if current_db_version == 0:
        return

    # default action is to upgrade scehma
    action = 'up'
    if desired_db_version < current_db_version:
        action = 'down'

    while current_db_version != desired_db_version:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(migration_scripts[current_db_version][action])

        current_db_version = get_db_version()
        # TODO: notify db migration step successful
