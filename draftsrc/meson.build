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
  'htmlstrings.py',
  'markup.py',
  'search.py',
  'thesaurus.py',
  'window.py'
]

db_sources = [
  'db/__init__.py',
  'db/data.py',
  'db/migrations.py',
  'db/requestqueue.py'
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

widgetmodels_sources = [
  'widgetmodels/grouptreestore.py',
  'widgetmodels/collectionliststore.py',
  'widgetmodels/textliststore.py'
]

views_sources = [
  'views/contentview.py',
  'views/__init__.py',
  'views/librarypanelview.py',
  'views/textpanelview.py'
]

widgets_sources = [
  'widgets/grouptree.py',
  'widgets/headerbar.py',
  'widgets/__init__.py',
  'widgets/collectionlist.py',
  'widgets/preview.py',
  'widgets/textlist.py',
]

install_data(app_sources, install_dir: draftsrcdir)
install_data(db_sources, install_dir: draftsrcdir + '/db')
install_data(editor_sources, install_dir: draftsrcdir + '/widgets/editor')
install_data(widgetmodels_sources, install_dir: draftsrcdir + '/widgetmodels')
install_data(views_sources, install_dir: draftsrcdir + '/views')
install_data(widgets_sources, install_dir: draftsrcdir + '/widgets')