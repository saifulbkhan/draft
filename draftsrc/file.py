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
from datetime import datetime
from contextlib import contextmanager

import gi
gi.require_version("GtkSource", "3.0")
from gi.repository import GtkSource, Gio, GLib

USER_DATA_DIR = join(GLib.get_user_data_dir(), 'draft')
BASE_TEXT_DIR = join(USER_DATA_DIR, 'texts', 'local')
TRASH_DIR = join(USER_DATA_DIR, 'texts', '.trash')

default_encoding = 'utf-8'


def init_storage():
    try:
        text_dir = join(USER_DATA_DIR, 'texts')
        Gio.file_new_for_path(text_dir).make_directory()
    except Exception:
        # TODO: Failed to make storage directory for texts or already exists
        pass

    try:
        text_local_dir = join(text_dir, 'local')
        Gio.file_new_for_path(text_local_dir).make_directory()
    except Exception:
        # TODO: Failed to make storage for local texts or already exists
        pass

    try:
        text_trash_dir = join(text_dir, '.trash')
        Gio.file_new_for_path(text_trash_dir).make_directory()
    except Exception as e:
        # TODO: Failed to make directory for trashed texts or already exists
       pass


def read_file_contents(filename, parent_names, buffer, load_file_cb):
    parent_dir = sep.join(parent_names)
    fpath = join(BASE_TEXT_DIR, parent_dir, filename)

    def load_finish_cb(loader, res, user_data):
        gsf = user_data
        try:
            success = loader.load_finish(res)
        except Exception as e:
            # TODO: Warn file read error so overwriting path with blank file...
            write_to_file(gsf.get_location(), "")
        finally:
            load_file_cb(gsf, buffer)

    f = Gio.File.new_for_path(fpath)
    gsf = GtkSource.File(location=f)
    loader = GtkSource.FileLoader.new(buffer, gsf)
    loader.load_async(GLib.PRIORITY_HIGH,
                      None, None, None,
                      load_finish_cb, gsf)


def write_to_file(f, contents):
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


def write_to_source_file_async(gsf, buffer):

    def write_buffer_cb(saver, res, user_data):
        try:
            success = saver.save_finish(res)
            if success:
                buffer.set_modified(False)
            else:
                raise IOError
        except Exception as e:
            # TODO: Warn write async failure
            pass

    saver = GtkSource.FileSaver.new(buffer, gsf)
    saver.save_async(GLib.PRIORITY_HIGH,
                     None, None, None,
                     write_buffer_cb, gsf)


def create_dir(dirname, parent_names):
    parent_dir = sep.join(parent_names)
    f_path = join(BASE_TEXT_DIR, parent_dir, dirname)
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
    src_path = join(BASE_TEXT_DIR, source_dir, filename)
    dest_path = join(BASE_TEXT_DIR, dest_dir, filename)
    move_from_src_to_dest(src_path, dest_path)


def trash_file(filename, parent_names, untrash=False):
    parent_dir = sep.join(parent_names)
    src_path = join(BASE_TEXT_DIR, parent_dir, filename)
    dest_path = join(TRASH_DIR, filename)
    if untrash:
        move_from_src_to_dest(dest_path, src_path)
    else:
        move_from_src_to_dest(src_path, dest_path)


@contextmanager
def make_backup(url):
    file = Gio.File.new_for_path(url)

    basename = file.get_basename()
    parentname = file.get_parent().get_path()
    backup_name = '.%s_%s' % (basename,
                              datetime.now().isoformat(timespec='milliseconds'))
    backup_path = join(parentname, backup_name)
    backup_file = Gio.File.new_for_path(backup_path)
    file.copy(backup_file, Gio.FileCopyFlags.OVERWRITE, None, None, None)

    try:
        yield
    except Exception as e:
        backup_file.copy(file, Gio.FileCopyFlags.OVERWRITE, None, None, None)
        # TODO (notify): something went wrong
    finally:
        backup_file.delete()