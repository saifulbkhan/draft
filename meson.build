project('noto',
	version: '0.1.0',
	meson_version: '>= 0.41.0')

project_id = 'org.gnome.Noto'

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
notosrcdir = join_paths(pythondir, 'notosrc')
icondir = join_paths(datadir, 'icons', 'hicolor')
schemadir = join_paths(datadir, 'glib-2.0', 'schemas')

conf = configuration_data()
conf.set('DATADIR', datadir)
conf.set('GSETTINGSSCHEMADIR', schemadir)
conf.set('LIBEXECDIR', libexecdir)
conf.set('LOCALEDIR', localedir)
conf.set('PYTHONDIR', pythondir)
conf.set('PKGDATADIR', pkgdatadir)
conf.set('MISTUNEDIR', join_paths(notosrcdir, 'mistune'))
conf.set('VERSION', meson.project_version())

configure_file(
	input: 'noto.in',
	output: 'noto',
	configuration: conf,
	install_dir: bindir
)

subdir('notosrc')
subdir('data')
subdir('po')

meson.add_install_script('meson_postinstall.py')
