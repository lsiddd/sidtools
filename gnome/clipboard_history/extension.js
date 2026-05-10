import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Pango from 'gi://Pango';
import St from 'gi://St';

import {Extension, gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const CLIPBOARD_TYPE = St.ClipboardType.CLIPBOARD;
const MAX_PREVIEW_LENGTH = 90;

function makePreview(text) {
    const preview = text.replace(/\s+/g, ' ').trim();

    if (preview.length <= MAX_PREVIEW_LENGTH)
        return preview;

    return `${preview.slice(0, MAX_PREVIEW_LENGTH - 1)}...`;
}

const ClipboardHistoryIndicator = GObject.registerClass(
class ClipboardHistoryIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, _('Clipboard History'));

        this._extension = extension;
        this._settings = extension.getSettings();
        this._clipboard = St.Clipboard.get_default();
        this._history = [];
        this._lastSeenText = null;
        this._timeoutId = 0;

        this.add_child(new St.Icon({
            icon_name: 'edit-paste-symbolic',
            style_class: 'system-status-icon',
        }));

        this.menu.connect('open-state-changed', (_menu, isOpen) => {
            if (isOpen) {
                this._pollClipboard();
                this._rebuildMenu();
            }
        });

        this._settingsChangedId = this._settings.connect('changed', () => {
            this._trimHistory();
            this._restartPolling();
            this._rebuildMenu();
        });

        this._restartPolling();
        this._pollClipboard();
        this._rebuildMenu();
    }

    destroy() {
        if (this._timeoutId) {
            GLib.Source.remove(this._timeoutId);
            this._timeoutId = 0;
        }

        if (this._settingsChangedId) {
            this._settings.disconnect(this._settingsChangedId);
            this._settingsChangedId = 0;
        }

        this.menu.removeAll();
        super.destroy();
    }

    _restartPolling() {
        if (this._timeoutId)
            GLib.Source.remove(this._timeoutId);

        const interval = this._settings.get_uint('poll-interval-seconds');
        this._timeoutId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            Math.max(1, interval),
            () => {
                this._pollClipboard();
                return GLib.SOURCE_CONTINUE;
            });
    }

    _pollClipboard() {
        this._clipboard.get_text(CLIPBOARD_TYPE, (_clipboard, text) => {
            if (typeof text !== 'string' || text.length === 0)
                return;

            if (text === this._lastSeenText)
                return;

            this._lastSeenText = text;
            this._addText(text);
        });
    }

    _addText(text) {
        const existingIndex = this._history.indexOf(text);
        if (existingIndex >= 0)
            this._history.splice(existingIndex, 1);

        this._history.unshift(text);
        this._trimHistory();

        if (this.menu.isOpen)
            this._rebuildMenu();
    }

    _trimHistory() {
        const maxItems = this._settings.get_uint('max-items');
        if (this._history.length > maxItems)
            this._history.length = maxItems;
    }

    _setClipboardText(text) {
        this._clipboard.set_text(CLIPBOARD_TYPE, text);
        this._lastSeenText = text;
        this._addText(text);
    }

    _rebuildMenu() {
        this.menu.removeAll();

        if (this._history.length === 0) {
            const emptyItem = new PopupMenu.PopupMenuItem(_('No copied text yet'), {
                reactive: false,
            });
            emptyItem.add_style_class_name('clipboard-history-empty-item');
            this.menu.addMenuItem(emptyItem);
            return;
        }

        for (const text of this._history) {
            const item = new PopupMenu.PopupMenuItem(makePreview(text));
            item.label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);
            item.label.clutter_text.set_single_line_mode(true);
            item.label.set_style('max-width: 420px;');
            item.connect('activate', () => this._setClipboardText(text));
            this.menu.addMenuItem(item);
        }

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this.menu.addAction(_('Clear History'), () => {
            this._history = [];
            this._lastSeenText = null;
            this._rebuildMenu();
        }, 'edit-clear-symbolic');
    }
});

export default class ClipboardHistoryExtension extends Extension {
    enable() {
        this._indicator = new ClipboardHistoryIndicator(this);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
