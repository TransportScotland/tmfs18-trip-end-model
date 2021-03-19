import PyInstaller.__main__

PyInstaller.__main__.run([
    '--name', 'TMfS18 Trip End Model',
    '--onefile',
    '--hidden-import', 'pkg_resources.py2_warn',
    # '--noconsole',  # comment out if errors occur, and run from command line
    'gui.py'
])
