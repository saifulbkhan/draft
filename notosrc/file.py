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

from os.path import join, sep
from gi.repository import Gio, GLib

from notosrc.data import USER_DATA_DIR

BASE_NOTE_DIR = join(USER_DATA_DIR, 'notes', 'local')
TRASH_DIR = join(USER_DATA_DIR, '.trash')

default_encoding = 'utf-8'


def read_file_contents(filename, parent_names):
    parent_dir = sep.join(parent_names)
    fpath = join(BASE_NOTE_DIR, parent_dir, filename)
    try:
        f = Gio.File.new_for_path(fpath)
        success, contents, etag = f.load_contents(None)
        if success:
            contents = contents.decode(default_encoding)
            return (f, contents, etag)
    except Exception as e:
        # TODO: Warn file IO error so overwriting path with blank file...
        f = Gio.File.new_for_path(fpath)
        etag = write_to_file(f, "", None)
        return (f, "", etag)

    return None


def write_to_file(f, contents, etag):
    contents = bytes(contents, default_encoding)
    try:
        success, etag = f.replace_contents(contents,
                                           etag,
                                           False,
                                           Gio.FileCreateFlags.PRIVATE,
                                           None)
        if success:
            return etag
    except Exception as e:
        # TODO: Warn write failure
        pass

    return None


def create_dir(dirname, parent_names):
    parent_dir = sep.join(parent_names)
    f_path = join(BASE_NOTE_DIR, parent_dir, filename)
    try:
        return Gio.File.new_for_path(f_path).make_directory_with_parents()
    except Exception as e:
        # TODO: Warn file create failure
        pass

    return None


def move_from_src_to_dest(src_path, dest_path):
    try:
        f_src = Gio.File.new_for_path(src_path)
        f_dest = Gio.File.new_for_path(dest_path)
        f_src.move(f_dest, Gio.FileCopyFlags.OVERWRITE, None, None, None)
    except Exception as e:
        # TODO: Warn file move failure
        return


def move_file(filename, src_parent_names, dest_parent_names):
    source_dir = sep.join(src_parent_names)
    dest_dir = sep.join(dest_parent_names)
    src_path = join(BASE_NOTE_DIR, source_dir, filename)
    dest_path = join(BASE_NOTE_DIR, dest_dir, filename)
    move_from_src_to_dest(src_path, dest_path)


def trash_file(filename, parent_names, untrash=False):
    parent_dir = sep.join(parent_names)
    src_path = join(BASE_NOTE_DIR, parent_dir, filename)
    dest_path = join(TRASH_DIR, filename)
    if untrash:
        move_from_src_to_dest(dest_path, src_path)
    else:
        move_from_src_to_dest(src_path, dest_path)
