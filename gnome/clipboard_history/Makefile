UUID := clipboard-history@sidtools.lucas
EXTENSION_DIR := $(HOME)/.local/share/gnome-shell/extensions/$(UUID)

.PHONY: install schemas pack clean

schemas:
	glib-compile-schemas schemas

install: schemas
	mkdir -p "$(EXTENSION_DIR)"
	cp -r extension.js metadata.json prefs.js schemas "$(EXTENSION_DIR)/"

pack: schemas
	gnome-extensions pack --force --schema=schemas/org.gnome.shell.extensions.clipboard-history.gschema.xml .

clean:
	rm -f "$(UUID).shell-extension.zip"
	rm -f schemas/gschemas.compiled
