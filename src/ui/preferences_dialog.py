"""
Preferences Dialog - Allows users to configure application settings.

This module provides a GTK dialog for managing application preferences,
such as the SSH config file path and future options.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject

class PreferencesDialog(Gtk.Dialog):
    """Dialog for application preferences."""
    
    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            modal=True,
            title="Preferences",
            default_width=400,
            default_height=200
        )
        
        self.set_resizable(False)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the preferences dialog user interface."""
        content_area = self.get_content_area()
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_row_homogeneous(False)
        grid.set_column_homogeneous(False)
        content_area.append(grid)
        
        config_path_label = Gtk.Label(label="SSH Config Path:", xalign=0)
        grid.attach(config_path_label, 0, 0, 1, 1)
        
        self.config_path_entry = Gtk.Entry()
        self.config_path_entry.set_placeholder_text("~/.ssh/config")
        self.config_path_entry.set_hexpand(True)
        grid.attach(self.config_path_entry, 1, 0, 1, 1)
        
        config_path_button = Gtk.Button()
        config_path_button.set_icon_name("document-open-symbolic")
        config_path_button.set_tooltip_text("Choose Config File")
        config_path_button.connect("clicked", self._on_config_path_clicked)
        grid.attach(config_path_button, 2, 0, 1, 1)
        
        backup_dir_label = Gtk.Label(label="Backup Directory:", xalign=0)
        grid.attach(backup_dir_label, 0, 1, 1, 1)
        self.backup_dir_entry = Gtk.Entry()
        self.backup_dir_entry.set_placeholder_text("~/.ssh")
        self.backup_dir_entry.set_hexpand(True)
        grid.attach(self.backup_dir_entry, 1, 1, 1, 1)
        backup_dir_button = Gtk.Button()
        backup_dir_button.set_icon_name("folder-open-symbolic")
        backup_dir_button.set_tooltip_text("Choose Backup Directory")
        backup_dir_button.connect("clicked", self._on_backup_dir_clicked)
        grid.attach(backup_dir_button, 2, 1, 1, 1)
        
        auto_backup_label = Gtk.Label(label="Enable Auto-Backup:", xalign=0)
        grid.attach(auto_backup_label, 0, 2, 1, 1)
        self.auto_backup_switch = Gtk.Switch()
        self.auto_backup_switch.set_active(True)
        self.auto_backup_switch.set_halign(Gtk.Align.START)
        grid.attach(self.auto_backup_switch, 1, 2, 1, 1)
        
        editor_font_label = Gtk.Label(label="Editor Font Size:", xalign=0)
        grid.attach(editor_font_label, 0, 3, 1, 1)
        self.editor_font_spin = Gtk.SpinButton()
        self.editor_font_spin.set_range(9, 24)
        self.editor_font_spin.set_increments(1, 2)
        self.editor_font_spin.set_value(12)
        grid.attach(self.editor_font_spin, 1, 3, 1, 1)
        
        theme_label = Gtk.Label(label="Prefer Dark Theme:", xalign=0)
        grid.attach(theme_label, 0, 4, 1, 1)
        self.dark_theme_switch = Gtk.Switch()
        self.dark_theme_switch.set_active(False)
        self.dark_theme_switch.set_halign(Gtk.Align.START)
        grid.attach(self.dark_theme_switch, 1, 4, 1, 1)
        
        self.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Save", Gtk.ResponseType.OK
        )
    
    def _connect_signals(self):
        """Connect signal handlers."""
        # Connect response signal to handle dialog closure
        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        # Handle Save/Cancel responses
        if response_id == Gtk.ResponseType.OK:
            # Preferences saving logic is now in main_window.
            pass
        dialog.destroy()

    def _on_config_path_clicked(self, button):
        """Handle config path file chooser button click."""
        dialog = Gtk.FileChooserDialog(
            title="Choose SSH Config File",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Open", Gtk.ResponseType.OK)
        
        dialog.connect("response", self._on_file_chooser_response)
        dialog.present()

    def _on_file_chooser_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            filename = dialog.get_file().get_path()
            self.config_path_entry.set_text(filename)
        dialog.destroy()

    def _on_backup_dir_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Choose Backup Directory",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Select", Gtk.ResponseType.OK)
        dialog.connect("response", self._on_backup_dir_response)
        dialog.present()

    def _on_backup_dir_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            folder = dialog.get_file()
            if folder:
                self.backup_dir_entry.set_text(folder.get_path())
        dialog.destroy()

    def get_preferences(self) -> dict:
        """Get current preference values."""
        return {
            "config_path": self.config_path_entry.get_text(),
            "backup_dir": self.backup_dir_entry.get_text(),
            "auto_backup": self.auto_backup_switch.get_active(),
            "editor_font_size": int(self.editor_font_spin.get_value()),
            "prefer_dark_theme": self.dark_theme_switch.get_active()
        }

    def set_preferences(self, prefs: dict):
        """Set preference values from a dictionary."""
        if "config_path" in prefs:
            self.config_path_entry.set_text(prefs["config_path"])
        if "backup_dir" in prefs:
            self.backup_dir_entry.set_text(prefs["backup_dir"])
        if "auto_backup" in prefs:
            self.auto_backup_switch.set_active(bool(prefs["auto_backup"]))
        if "editor_font_size" in prefs:
            self.editor_font_spin.set_value(float(prefs["editor_font_size"]))
        if "prefer_dark_theme" in prefs:
            self.dark_theme_switch.set_active(bool(prefs["prefer_dark_theme"]))
