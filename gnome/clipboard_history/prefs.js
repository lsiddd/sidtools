import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class ClipboardHistoryPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();

        const page = new Adw.PreferencesPage({
            title: _('Clipboard History'),
            icon_name: 'edit-paste-symbolic',
        });

        const group = new Adw.PreferencesGroup({
            title: _('History'),
        });

        const maxItemsRow = new Adw.ActionRow({
            title: _('Items to keep'),
            subtitle: _('Maximum number of copied text items shown in the panel menu.'),
        });
        const maxItemsSpin = new Gtk.SpinButton({
            adjustment: new Gtk.Adjustment({
                lower: 1,
                upper: 100,
                step_increment: 1,
                page_increment: 5,
            }),
            valign: Gtk.Align.CENTER,
            numeric: true,
        });
        settings.bind('max-items', maxItemsSpin, 'value', Gio.SettingsBindFlags.DEFAULT);
        maxItemsRow.add_suffix(maxItemsSpin);
        maxItemsRow.activatable_widget = maxItemsSpin;
        group.add(maxItemsRow);

        const pollIntervalRow = new Adw.ActionRow({
            title: _('Polling interval'),
            subtitle: _('Seconds between clipboard checks.'),
        });
        const pollIntervalSpin = new Gtk.SpinButton({
            adjustment: new Gtk.Adjustment({
                lower: 1,
                upper: 10,
                step_increment: 1,
                page_increment: 1,
            }),
            valign: Gtk.Align.CENTER,
            numeric: true,
        });
        settings.bind('poll-interval-seconds', pollIntervalSpin, 'value',
            Gio.SettingsBindFlags.DEFAULT);
        pollIntervalRow.add_suffix(pollIntervalSpin);
        pollIntervalRow.activatable_widget = pollIntervalSpin;
        group.add(pollIntervalRow);

        page.add(group);
        window.add(page);
    }
}
