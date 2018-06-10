gnome = import('gnome')

message('Compiling resources')

gnome.compile_resources(
  meson.project_name(),
  meson.project_name() + '.gresource.xml',
  gresource_bundle: true,
  source_dir: '.',
  install_dir: datadir,
  install: true,
  dependencies: configure_file(
    input: 'aboutdialog.ui.in',
    output: 'aboutdialog.ui',
    configuration: conf
  )
)

message('Installing schemas')
gnome.compile_schemas()
install_data(
  project_id + '.gschema.xml',
  install_dir: join_paths(datadir, 'glib-2.0/schemas')
)

message('Installing KaTeX')
install_subdir(
  'katex',
  install_dir: join_paths(datadir, 'draft')
)

message('Installing stylesheets')
install_subdir(
  'styles',
  install_dir: join_paths(datadir, 'draft')
)

subdir('icons')

# TODO: Making a desktop file
# TODO: Preparing appdata
