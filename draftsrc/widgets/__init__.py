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

from gi.repository import Gtk

GROUP_MOVE_INFO = 0
TEXT_MOVE_INFO = 1
GROUP_MOVE_TARGET = Gtk.TargetEntry.new("group-path",
                                        Gtk.TargetFlags.SAME_WIDGET,
                                        GROUP_MOVE_INFO)
TEXT_MOVE_TARGET = Gtk.TargetEntry.new("text-position",
                                       Gtk.TargetFlags.SAME_APP,
                                       TEXT_MOVE_INFO)
