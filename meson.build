project('draft',
	version: '0.1.0',
	meson_version: '>= 0.41.0')

project_id = 'org.gnome.Draft'

i18n = import('i18n')
python3 = import('python3')

python_bin = python3.find_python()
prefix = get_option('prefix')

bindir = join_paths(prefix, get_option('bindir'))
datadir = join_paths(prefix, get_option('datadir'))
libexecdir = join_paths(prefix, get_option('libexecdir'))
localedir = join_paths(prefix, get_option('localedir'))
pythondir = join_paths(prefix, python3.sysconfig_path('purelib'))

pkgdatadir = join_paths(datadir, meson.project_name())

appdatadir = join_paths(datadir, 'metainfo')
desktopdir = join_paths(datadir, 'applications')
draftsrcdir = join_paths(pythondir, 'draftsrc')
icondir = join_paths(datadir, 'icons', 'hicolor')
schemadir = join_paths(datadir, 'glib-2.0', 'schemas')

conf = configuration_data()
conf.set('DATADIR', datadir)
conf.set('GSETTINGSSCHEMADIR', schemadir)
conf.set('LIBEXECDIR', libexecdir)
conf.set('LOCALEDIR', localedir)
conf.set('PYTHONDIR', pythondir)
conf.set('PKGDATADIR', pkgdatadir)
conf.set('UTILSDIR', join_paths(draftsrcdir, 'utils'))
conf.set('WEBUTILSDIR', join_paths(draftsrcdir, 'webutils'))
conf.set('VERSION', meson.project_version())

configure_file(
	input: 'draft.in',
	output: 'draft',
	configuration: conf,
	install_dir: bindir
)

subproject('wkjscore-result')
subdir('draftsrc')
subdir('data')
subdir('po')

meson.add_install_script('meson_postinstall.py')
