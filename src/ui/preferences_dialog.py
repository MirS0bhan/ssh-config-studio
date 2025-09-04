
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject, Adw
from gettext import gettext as _

@Gtk.Template(resource_path="/com/sshconfigstudio/app/ui/preferences_dialog.ui")
class PreferencesDialog(Adw.PreferencesWindow):
    """Application preferences dialog using Adwaita components."""
    
    __gtype_name__ = "PreferencesDialog"

    config_path_entry = Gtk.Template.Child()
    config_path_button = Gtk.Template.Child()
    backup_dir_entry = Gtk.Template.Child()
    backup_dir_button = Gtk.Template.Child()
    auto_backup_switch = Gtk.Template.Child()
    editor_font_spin = Gtk.Template.Child()
    dark_theme_switch = Gtk.Template.Child()
    raw_wrap_switch = Gtk.Template.Child()

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            modal=True,
            title=_("Preferences")
        )
        self.set_default_size(600, 500)
        self._connect_signals()
    
    def _connect_signals(self):
        self.config_path_button.connect("clicked", self._on_config_path_clicked)
        self.backup_dir_button.connect("clicked", self._on_backup_dir_clicked)

    def _on_config_path_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Choose SSH Config File"),
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Open"), Gtk.ResponseType.OK)
        dialog.connect("response", self._on_file_chooser_response)
        dialog.present()

    def _on_file_chooser_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            filename = dialog.get_file().get_path()
            self.config_path_entry.set_text(filename)
        dialog.destroy()

    def _on_backup_dir_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Choose Backup Directory"),
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Select"), Gtk.ResponseType.OK)
        dialog.connect("response", self._on_backup_dir_response)
        dialog.present()

    def _on_backup_dir_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            folder = dialog.get_file()
            if folder:
                self.backup_dir_entry.set_text(folder.get_path())
        dialog.destroy()

    def get_preferences(self) -> dict:
        return {
            "config_path": self.config_path_entry.get_text(),
            "backup_dir": self.backup_dir_entry.get_text(),
            "auto_backup": self.auto_backup_switch.get_active(),
            "editor_font_size": int(self.editor_font_spin.get_value()),
            "prefer_dark_theme": self.dark_theme_switch.get_active(),
            "raw_wrap_lines": self.raw_wrap_switch.get_active()
        }

    def set_preferences(self, prefs: dict):
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
        if "raw_wrap_lines" in prefs:
            self.raw_wrap_switch.set_active(bool(prefs["raw_wrap_lines"]))
