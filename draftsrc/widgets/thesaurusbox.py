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

from gi.repository import Gtk, GObject, Gdk

from draftsrc import thesaurus


class DraftThesaurusBox(Gtk.Box):
    __gtype_name__ = 'DraftThesaurusBox'

    __gsignals__ = {
        'cancel-synonym': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'apply-synonym': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          (GObject.TYPE_STRING,))
    }

    _language_tag = ''
    _language_packs = {}
    _synboxes = []
    _selected_box_and_child = ()
    _selected_synonym = ''
    _current_word = ''

    def __repr__(self):
        return '<DraftThesaurusBox>'

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Draft/thesaurusbox.ui')

        self._topbar = builder.get_object('topbar')
        self._scrolled = builder.get_object('scrolled')
        self._title_label = builder.get_object('title_label')
        self._cancel_button = builder.get_object('cancel_button')
        self._apply_button = builder.get_object('apply_button')
        self._language_button = builder.get_object('language_button')
        self._language_popover = builder.get_object('language_popover')
        self._language_scrolled = builder.get_object('language_scrolled')
        self._synset_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.add(self._topbar)
        self.add(self._scrolled)
        self._scrolled.add(self._synset_box)

        self._cancel_button.connect('clicked', self._on_cancel_clicked)
        self._apply_button.connect('clicked', self._on_apply_clicked)
        self._language_button.connect('clicked', self._on_language_clicked)
        self._language_popover.connect('closed', self._on_popover_closed)

        self.set_language_for_thesaurus()

        self.get_style_context().add_class('draft-thesaurus-box')

    def set_language_for_thesaurus(self, language_tag=''):
        if not language_tag:
            language_tag, __ = thesaurus.current_user_language()
        self._language_tag = language_tag

        language, country = thesaurus.language_region_for_tag(language_tag)
        self._language_button.set_label('%s (%s)' % (language, country))
        self.update_for_word(self._current_word)

    def update_language_packs_available(self):
        self._language_packs = {}
        language_tags = thesaurus.available_language_packs()
        for langtag in language_tags:
            language, country = thesaurus.language_region_for_tag(langtag)
            langstring = '%s (%s)' % (language, country)
            self._language_packs[langstring] = langtag

    def update_for_word(self, word):
        self._current_word = word
        children = self._synset_box.get_children()
        for child in children:
            self._synset_box.remove(child)

        synsets = thesaurus.get_synonymous_words(word, self._language_tag)
        if synsets is None:
            self._scrolled.set_visible(False)
            self._title_label.set_markup(_("<big><big>No synonyms found for <b>“%s”</b></big></big>") % word)
            self._apply_button.set_visible(False)
            return

        self._scrolled.set_visible(True)
        self._title_label.set_markup(_("<big><big>Synonyms for <b>“%s”</b></big></big>") % word)
        self._apply_button.set_visible(True)

        for synset in synsets:
            pos, words = synset

            label = Gtk.Label()
            label.set_markup("<span fgalpha=\"60%%\"><big><b>%s</b></big></span>" % pos)
            label.set_halign(Gtk.Align.START)

            flowbox = Gtk.FlowBox()
            flowbox.set_orientation(Gtk.Orientation.HORIZONTAL)
            flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            flowbox.set_column_spacing(8)
            flowbox.set_row_spacing(8)

            for word in words:
                syn_label = Gtk.Label(word)
                syn_label.set_halign(Gtk.Align.START)
                flowbox.add(syn_label)

            # to prevent some erratic experience, disable focus based navigation
            for child in flowbox.get_children():
                child.get_style_context().add_class('draft-synonym')
                child.set_can_focus(False)

            flowbox.connect('child-activated', self._on_synonym_activated)
            self._synboxes.append(flowbox)

            wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            wrapper.set_spacing(6)
            wrapper.add(label)
            wrapper.add(flowbox)
            wrapper.get_style_context().add_class('draft-synbox')
            self._synset_box.add(wrapper)

        self._synset_box.show_all()

    def _on_synonym_activated(self, flowbox, child):
        if self._selected_box_and_child:
            box, boxchild = self._selected_box_and_child
            if flowbox is box and child is boxchild:
                flowbox.unselect_child(child)
                self._selected_synonym = ''
                self._selected_box_and_child = ()
                self._apply_button.set_sensitive(False)
                return

        for box in self._synboxes:
            if box is not flowbox:
                box.unselect_all()

        label = child.get_child()
        self._selected_synonym = label.get_label()
        self._selected_box_and_child = (flowbox, child)
        self._apply_button.set_sensitive(True)

    def _on_cancel_clicked(self, widget):
        self.emit('cancel-synonym')

    def _on_apply_clicked(self, widget):
        synonym = self._selected_synonym

        # if the label contains bracketed terms, remove them, since they are
        # unlikely to be part of the actual synonym.
        left_bracket_index = synonym.find('(')
        right_bracket_index = synonym.find(')')
        if left_bracket_index != -1 and right_bracket_index != -1:
            synonym = synonym[:left_bracket_index]

        # try to match the case
        if self._current_word and self._current_word[0].isupper():
            synonym = synonym.capitalize()
        elif self._current_word and self._current_word[0].islower():
            synonym = synonym.lower()

        self.emit('apply-synonym', synonym.strip())

    def _on_language_clicked(self, widget):
        child = self._language_scrolled.get_child()
        if child is not None:
            self._language_scrolled.remove(child)

        self.update_language_packs_available()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for language in self._language_packs:
            button = Gtk.ModelButton()
            button.set_label(language)
            label = button.get_child()
            label.set_halign(Gtk.Align.START)
            box.add(button)
            button.connect('pressed', self._on_language_selected)

        box.show_all()

        self._language_scrolled.add(box)
        self._language_popover.popup()

    def _on_language_selected(self, button):
        language = button.get_label()
        self.set_language_for_thesaurus(self._language_packs[language])

    def _on_popover_closed(self, widget):
        self._language_button.set_active(False)
