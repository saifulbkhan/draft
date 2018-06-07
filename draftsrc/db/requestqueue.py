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
from collections import OrderedDict

from draftsrc import db


class RequestQueue(OrderedDict):
    """A dict with queue like FIFO methods, and supports asynchronous work
    to be done with the items contained within."""
    active = False

    def __init__(self, async=True, immediate_activation=True):
        super().__init__()
        self.async = async
        self.immediate_activation = immediate_activation

    def enqueue(self, key, val):
        """Put an item in queue with a unique key. If the queue was empty and
        should immeadiately be working on the requests, activate it."""
        self[key] = val
        if not self.active and self.immediate_activation:
            self.activate()

    def remove_if_exists(self, key):
        """Remove the item with given key if it exists"""
        if key in self:
            self.pop(key)

    def activate(self):
        """Work on the contents of the queue, in a separate thread."""
        self.active = True
        if self.async:
            thread = threading.Thread(target=self.do_work)
            thread.daemon = True
            thread.start()
        else:
            self.do_work()

    def dequeue(self):
        """Get the oldest item inserted into the queue."""
        key, val = None, None
        if len(self):
            key, val = self.popitem(last=False)

        return key, val

    def do_work(self):
        """Defines what should be done with the items in queue. This method
        must be defined by subclasses accordingly."""
        self.active = False


class UpdateRequestQueue(RequestQueue):
    """A RequestQueue meant for performing updates to the database."""
    execution_fn = None
    fetch_fn = None

    def do_work(self):
        """Loop over the queue and for each item perform `execution_fn`
        operation."""
        if self.execution_fn is None:
            self.active = False
            return

        while True:
            id, values = self.dequeue()
            if not (id and values):
                break

            with db.connect() as connection:
                if self.fetch_fn:
                    try:
                        current_values = self.fetch_fn(connection, id)
                        last_modified = db.get_datetime_from_string(current_values['last_modified'])
                        new_last_modified = db.get_datetime_from_string(values['last_modified'])
                        if last_modified > new_last_modified:
                            continue
                    except Exception as e:
                         # (notify): maybe text with given id does not exist,
                         # or some other sqlite exception; regardless it is
                         # unsafe to proceed with update execution -- skip this.
                         continue

                self.execution_fn(connection, id, values)

        self.active = False


class DeleteRequestQueue(RequestQueue):
    """A RequestQueue for async deletion of items from the database"""
    deletion_fn = None

    def do_work(self):
        """Loop over the queue and perform `deletion_fn` for each of the
        items"""
        if self.deletion_fn is None:
            self.active = False
            return

        while True:
            id, values = self.dequeue()
            if id is None:
                break

            with db.connect() as connection:
                self.deletion_fn(connection, id)

        self.active = False
