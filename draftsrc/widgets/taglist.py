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

from gettext import gettext as _

from gi.repository import Gtk, GObject, Pango

from draftsrc.models.tagliststore import DraftTagListStore


class DraftTagList(Gtk.ListBox):
    """A listbox containing all tags attached to texts not in trash"""
    __gtype_name__ = 'DraftTagList'

    __gsignals__ = {
        'tag-selected': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         (GObject.TYPE_PYOBJECT,)),
        'list-changed': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<DraftTagList>'

    def __init__(self):
        Gtk.ListBox.__init__(self)
        self.connect('row-activated', self._on_row_selected)
        self._model = DraftTagListStore()
        self.bind_model(self._model, self._create_row_widget, None)
        ctx = self.get_style_context()
        ctx.add_class('draft-taglist')

    def _create_row_widget(self, tag_data, user_data):
        """Create a row widget in the ListBox with supplied tag data"""
        data_dict = tag_data.to_dict()

        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctx = row_box.get_style_context()
        ctx.add_class('draft-tag-box-row')

        label = Gtk.Label()
        row_box.pack_start(label, True, False, 0)
        self._set_tag_label(row_box, data_dict['keyword'])

        return row_box

    def _set_tag_label(self, box, label_name):
        """Set label shown for tag"""
        children = box.get_children()
        label = children[0]
        label.set_markup('%s' % label_name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_halign(Gtk.Align.START)
        label.set_visible(True)

    def _on_row_selected(self, widget, row):
        position = row.get_index()
        tag = self._model.get_data_for_position(position)
        self.emit('tag-selected', tag)

    def select_if_not_selected(self):
        """Select the first tag in list if none is selected"""
        row = self.get_selected_row()
        if row is None:
            row = self.get_row_at_index(0)
            self.select_row(row)
        row.activate()
        row.grab_focus()

    def get_num_tags_in_list(self):
        """Obtain the number of items in the list"""
        return self._model.get_n_items()

    def update_state(self, tags):
        """Update model to reflect changes done by addition or exclusion of tags
        through various different operations. This method can handle addition or
        deletion of tags from texts, trashing of texts (in which case an empty
        list is provided in place of @tags) and restoring of texts from trash
        (in which case the combination of the tags from restored texts is
        supplied for @tags)"""
        had_selected_row = bool(self.get_selected_row())
        self._model.update(tags)
        self.emit('list-changed')

        # from here on, we assume that all labels in tags have a
        # place in the model
        def select_first_tag_in_tags():
            label = tags[0]
            tag_position = self._model.get_position_for_tag(label)
            row = self.get_row_at_index(tag_position)
            if row:
                self.select_row(row)
                row.activate()

        selected_row = self.get_selected_row()
        if tags and not selected_row and had_selected_row:
            select_first_tag_in_tags()
        elif not tags and not selected_row and had_selected_row:
            self.select_if_not_selected()
        elif not selected_row:
            return
        else:
            selected_position = selected_row.get_index()
            selected_tag = self._model.get_data_for_position(selected_position)
            if tags and selected_tag['keyword'] not in tags:
                select_first_tag_in_tags()
            elif not tags:
                self.select_if_not_selected()
