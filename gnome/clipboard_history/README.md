# Clipboard History

GNOME Shell extension that adds a panel indicator for recently copied text.

## Features

- Keeps the latest copied text items in memory.
- Lets you pick an item from the panel menu to put it back on the clipboard.
- Moves reused items back to the top.
- Configurable history size and polling interval.
- Clear-history action from the menu.

The extension currently tracks text clipboard contents only.

## Install locally

```sh
make install
gnome-extensions enable clipboard-history@sidtools.lucas
```

On X11, restart GNOME Shell with `Alt+F2`, `r`, Enter. On Wayland, log out and log back in if the extension does not appear immediately.

## Preferences

Open the preferences with:

```sh
gnome-extensions prefs clipboard-history@sidtools.lucas
```
