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
	'textview.py',
	'markdown.py',
	'webview.py',
	'window.py'
]

utils_sources = [
	'utils/__init__.py',
	'utils/mistune.py',
	'utils/gi_composites.py'
]

static_sources = [
	'static/content.py',
	'static/static.js'
]

install_data(app_sources, install_dir: notosrcdir)
install_data(utils_sources, install_dir: notosrcdir + '/utils')
install_data(static_sources, install_dir: notosrcdir + '/static')
