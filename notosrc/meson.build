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
	'datamodel.py',
	'data.py',
	'file.py',
	'store.py',
	'contentview.py',
	'notesview.py',
	'editor.py',
	'markdown.py',
	'webview.py',
	'window.py'
]

utils_sources = [
	'utils/__init__.py',
	'utils/mistune.py'
]

webutils_sources = [
	'webutils/content.py',
]

install_data(app_sources, install_dir: notosrcdir)
install_data(utils_sources, install_dir: notosrcdir + '/utils')
install_data(webutils_sources, install_dir: notosrcdir + '/webutils')
