configure_file(
  input: 'defs.py.in',
  output: 'defs.py',
  configuration: conf,
  install: true,
  install_dir: draftsrcdir
)

app_sources = [
  '__init__.py',
  'app.py',
  'file.py',
  'window.py'
]

db_sources = [
  'db/__init__.py',
  'db/data.py',
  'db/migrations.py'
]

parsers_sources = [
  'parsers/__init__.py',
  'parsers/markup.py',
  'parsers/mistune.py',
  'parsers/webstrings.py'
]

views_sources = [
  'views/contentview.py',
  'views/panelview.py',
  'views/store.py'
]

widgets_sources = [
  'widgets/editor.py',
  'widgets/grouptree.py',
  'widgets/__init__.py',
  'widgets/preview.py',
  'widgets/statusbar.py',
  'widgets/textlist.py'
]

install_data(app_sources, install_dir: draftsrcdir)
install_data(db_sources, install_dir: draftsrcdir + '/db')
install_data(parsers_sources, install_dir: draftsrcdir + '/parsers')
install_data(views_sources, install_dir: draftsrcdir + '/views')
install_data(widgets_sources, install_dir: draftsrcdir + '/widgets')
