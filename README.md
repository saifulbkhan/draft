## Draft

Draft is a markup-based writing application meant to be used by writers and
academics. However, it is a bit too early in its development stage to be used by
either of those people. At the moment, Draft provides the following features:
- organizing "Texts" (sheets) into "Groups"
- tagging texts with labels
- preview and export HTML equivalent of text markup
- markdown support in editor with a cheatsheet for reference
- LaTeX math support
- spell checking
- thesaurus lookup
- word goals
- search for text content/tags.
- and an (experimental) typewriter mode.

The author would like to have a bit more utility than the above mentioned
features as well as more stability before recommending it for general usage.
If you try it out and find issues please report them (see
[contributing](#contributing)).


### Building the application

To build Draft, the following **dependencies** are needed:
- `gtk3 >= 3.20`
- `gobject-introspection`
- `gtksourceview3 >= 3.24`
- `gspell`
- `python3`
- `pygobject3`
- `meson >= 0.41`
- `ninja`
- `python3-cairo`
- `python3-mistune`
- `python3-whoosh`

Some **optional dependencies** required for additional features:
- `mythes` (for thesaurus along with preferred language pack)
- `python3-pygments` (for syntax highlighting in preview mode)

For now, the only way to try out the app is to build from source:
```shell
git clone https://github.com/saifulbkhan/draft.git
cd draft
```

Now if one does not want to pollute their system with unstable software, they
can install it locally. For example, to install it to the common alternative
prefix `$HOME/.local` we can use the following set of commands:
```shell
meson build --prefix=$HOME/.local
ninja -C build install
```

... or they can install Draft system-wide:
```shell
meson build
sudo ninja -C build install
```


### Contributing

Draft is far from complete. In fact, in its current state it appears to be a
glorified markdown-to-html converter. But there is room for much growth and
refinement. Features like - being able to export to commonly used formats (other
than HTML), live preview, cloud-based synchronization and maybe even a document
version control would be welcome additions. The editor can also be polished for
a much better writing experience. Same goes for Group and Sheet views, which are
not as interactive as they ought to be. These ideas seem ambiguous and more like
wishful thinking, but stay tuned for details on each of these goals. If a
contributor would like to work on any of them, please create an
[issue](https://github.com/saifulbkhan/draft/issues) and we can talk about it in
depth.

That said, there must be plenty of bugs hanging around as well. Known ones are
being looked at. [Reporting](https://github.com/saifulbkhan/draft/issues) and
working on bugs would be even more appreciated -- let's try to create a more
stable product before bringing in even more features and increasing the
complexity.

Any form of help and constructive criticisms are definitely welcome.
