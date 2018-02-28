configure_file(
  input: 'defs.py.in',
  output: 'defs.py',
  configuration: conf,
  install: true,
  install_dir: notosrcdir
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
  'views/listview.py',
  'views/store.py'
]

widgets_sources = [
  'widgets/editor.py',
  'widgets/preview.py',
  'widgets/statusbar.py'
]

install_data(app_sources, install_dir: notosrcdir)
install_data(db_sources, install_dir: notosrcdir + '/db')
install_data(parsers_sources, install_dir: notosrcdir + '/parsers')
install_data(views_sources, install_dir: notosrcdir + '/views')
install_data(widgets_sources, install_dir: notosrcdir + '/widgets')
