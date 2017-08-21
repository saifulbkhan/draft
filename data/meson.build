gnome = import('gnome')

message('Compiling resources')

gnome.compile_resources(
  meson.project_name(),
  meson.project_name() + '.gresource.xml',
  gresource_bundle: true,
  source_dir: '.',
  install_dir: datadir,
  install: true,
)

message('Installing schemas')
gnome.compile_schemas()
install_data(
  project_id + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)

# TODO: Making a desktop file
# TODO: Preparing appdata
# TODO: Install icons
