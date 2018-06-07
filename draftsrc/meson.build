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
  'export.py',
  'file.py',
  'search.py',
  'thesaurus.py',
  'window.py'
]

db_sources = [
  'db/__init__.py',
  'db/data.py',
  'db/migrations.py'
]

editor_sources = [
  'widgets/editor/__init__.py',
  'widgets/editor/editor.py',
  'widgets/editor/searchbox.py',
  'widgets/editor/sourcebuffer.py',
  'widgets/editor/sourceview.py',
  'widgets/editor/statusbar.py',
  'widgets/editor/thesaurusbox.py'
]

models_sources = [
  'models/grouptreestore.py',
  'models/collectionliststore.py',
  'models/textliststore.py'
]

parsers_sources = [
  'parsers/__init__.py',
  'parsers/markup.py',
  'parsers/mistune.py',
  'parsers/webstrings.py'
]

views_sources = [
  'views/contentview.py',
  'views/panelview.py'
]

widgets_sources = [
  'widgets/grouptree.py',
  'widgets/__init__.py',
  'widgets/collectionlist.py',
  'widgets/preview.py',
  'widgets/textlist.py',
]

install_data(app_sources, install_dir: draftsrcdir)
install_data(db_sources, install_dir: draftsrcdir + '/db')
install_data(editor_sources, install_dir: draftsrcdir + '/widgets/editor')
install_data(models_sources, install_dir: draftsrcdir + '/models')
install_data(parsers_sources, install_dir: draftsrcdir + '/parsers')
install_data(views_sources, install_dir: draftsrcdir + '/views')
install_data(widgets_sources, install_dir: draftsrcdir + '/widgets')
