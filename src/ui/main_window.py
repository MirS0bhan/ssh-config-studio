import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, GLib, Pango, GdkPixbuf, Gdk, Adw
from pathlib import Path
from gettext import gettext as _
import sys

from .host_list import HostList
from .host_editor import HostEditor
from .search_bar import SearchBar

@Gtk.Template(resource_path="/com/sshconfigstudio/app/ui/main_window.ui")
class MainWindow(Adw.ApplicationWindow):
    """Main application window for SSH Config Studio."""
    
    __gtype_name__ = "MainWindow"

    # Template children
    main_box = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    search_button = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    host_list = Gtk.Template.Child()
    host_editor = Gtk.Template.Child()
    save_button = Gtk.Template.Child()

    def __init__(self, app):
        super().__init__(
            application=app,
        )
        
        self.app = app
        self.parser = app.parser
        self.is_dirty = False
        
        self._connect_signals()
        self._load_config()
        
        self.connect("notify::has-focus", self._on_window_focus_changed)
        
        try:
            key_controller = Gtk.EventControllerKey.new()
            key_controller.connect("key-pressed", self._on_key_pressed)
            self.add_controller(key_controller)
        except Exception:
            pass
    
    
    
    def show_toast(self, message: str):
        """Show a transient toast using Adw.ToastOverlay."""
        try:
            toast = Adw.Toast.new(message)
            if hasattr(self, 'toast_overlay') and self.toast_overlay is not None:
                self.toast_overlay.add_toast(toast)
        except Exception:
            pass
    
    def _setup_split_view(self):
        """Set up the split view between host list and editor."""
        self.host_list = HostList()
        self.host_editor = HostEditor()
        try:
            self.host_editor.set_app(self.app)
        except Exception:
            # Host editor will operate without app reference
            return
        
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(self.host_list)
        paned.set_end_child(self.host_editor)
        paned.set_position(400)
        
        self.main_box.append(paned)
    
    def _connect_signals(self):
        """Connect all the signal handlers."""
        try:
            self.save_button.connect("clicked", self._on_save_clicked)
        except Exception:
            pass
        try:
            self.search_button.connect("clicked", self._on_search_button_clicked)
        except Exception:
            pass
        self.host_list.connect("host-selected", self._on_host_selected)
        self.host_list.connect("host-added", self._on_host_added)
        self.host_list.connect("host-deleted", self._on_host_deleted)
        
        self.host_editor.connect("host-changed", self._on_host_changed)
        self.host_editor.connect("editor-validity-changed", self._on_editor_validity_changed)
        
        self.search_bar.connect("search-changed", self._on_search_changed)
        
        self._setup_actions()
    
    def _setup_actions(self):
        """Set up application actions."""
        actions = Gio.SimpleActionGroup()
        
        open_action = Gio.SimpleAction.new("open-config", None)
        open_action.connect("activate", self._on_open_config)
        actions.add_action(open_action)
        
        reload_action = Gio.SimpleAction.new("reload", None)
        reload_action.connect("activate", self._on_reload)
        actions.add_action(reload_action)
        
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        actions.add_action(prefs_action)
        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        actions.add_action(about_action)
        
        search_action = Gio.SimpleAction.new("search", None)
        search_action.connect("activate", self._on_search_action)
        actions.add_action(search_action)
        
        self.insert_action_group("app", actions)
        
        try:
            app = self.get_application() or self.app
            if app is not None:
                app.set_accels_for_action("app.search", ["<primary>f"])
        except Exception:
            pass
    
    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape and self.search_bar.get_visible():
            self.search_bar.clear_search()
            self.search_bar.set_visible(False)
            self.host_list.filter_hosts("")
            return True
        return False
    
    def _on_escape_pressed(self, shortcut):
        """Handle Escape key press - close search bar if visible."""
        if self.search_bar.get_visible():
            self.search_bar.clear_search()
            self.search_bar.set_visible(False)
            self.host_list.filter_hosts("")
    
    def _load_config(self):
        """Load the SSH configuration."""
        if not self.parser:
            return
        
        try:
            self.parser.parse()
            self.host_list.load_hosts(self.parser.config.hosts)
            self._update_status("Configuration loaded successfully")
        except Exception as e:
            self._show_error(f"Failed to load configuration: {e}")
    
    def _toggle_search(self, force=None):
        """Show/hide search bar. If force is None, toggle; else set visibility to force."""
        try:
            make_visible = (not self.search_bar.get_visible()) if force is None else bool(force)
            self.search_bar.set_visible(make_visible)
            if make_visible:
                self.search_bar.grab_focus()
            else:
                self.search_bar.clear_search()
                self.host_list.filter_hosts("")
        except Exception:
            pass

    def _on_search_button_clicked(self, button):
        """Handle search button click."""
        self._toggle_search()

    def _on_search_action(self, action, param):
        """Handle app.search action (keyboard/menu)."""
        self._toggle_search()
    
    def _on_window_focus_changed(self, window, param):
        """Hide search bar if window loses focus."""
        if not self.get_has_focus() and self.search_bar.get_visible():
            self.search_bar.clear_search()
            self.search_bar.set_visible(False)
            self.host_list.filter_hosts("")
    
    # Deprecated: status bar close is no longer used with toasts
    def on_status_bar_close_clicked(self, button):
        pass
    
    def _on_save_clicked(self, button):
        if not self.parser:
            return
        try:
            errors = self.parser.validate()
            if errors:
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="Validation warnings",
                    secondary_text="\n".join(errors)
                )
                dialog.connect("response", lambda d, r: d.destroy())
                dialog.present()
            self.parser.write(backup=True)
            self.parser.parse()
            
            self.host_list.load_hosts(self.parser.config.hosts)
            self.is_dirty = False
            self.save_button.set_sensitive(False)
            self._update_status(_("Configuration saved successfully"))
        except Exception as e:
            self._show_error(f"Failed to save configuration: {e}")
    
    def _on_host_selected(self, host_list, host):
        """Handle host selection from the list."""
        self.host_editor.load_host(host)
        self.host_editor.set_visible(True)

    def _on_host_added(self, host_list, host):
        if self.parser:
            base_pattern = "new-host"
            i = 0
            new_pattern = base_pattern
            existing_patterns = {p for h in self.parser.config.hosts for p in h.patterns}
            while new_pattern in existing_patterns:
                i += 1
                new_pattern = f"{base_pattern}-{i}"
            host.patterns = [new_pattern]
            host.raw_lines = [f"Host {new_pattern}"]

            self.parser.config.add_host(host)
            self.is_dirty = True
            self.save_button.set_sensitive(True)
            self._update_status(_("Host added"))
            self.host_editor.set_visible(True)
            self.host_editor.load_host(host)
    
    def _on_host_deleted(self, host_list, host):
        """Handle host deletion."""
        if self.parser:
            self.parser.config.remove_host(host)
            self.is_dirty = True
            self.save_button.set_sensitive(True)
            self._update_status(_("Host deleted"))
            
            if not self.parser.config.hosts:
                self.host_editor.current_host = None
                self.host_editor._clear_all_fields()
                self.host_editor.set_visible(False)
                self.save_button.set_sensitive(False)
                self.is_dirty = False
            else:
                self.host_list.select_host(self.parser.config.hosts[0])
    
    def _on_host_changed(self, editor, host):
        self.is_dirty = self.parser.config.is_dirty()
        self.save_button.set_sensitive(self.is_dirty)

    def _on_editor_validity_changed(self, editor, is_valid: bool):
        if not is_valid:
            self.save_button.set_sensitive(False)
        else:
            self.save_button.set_sensitive(self.is_dirty)

    def _on_search_changed(self, search_bar, query):
        """Handle search query changes."""
        self.host_list.filter_hosts(query)
    
    def _on_open_config(self, action, param):
        """Handle open config action."""
        dialog = Gtk.FileChooserNative.new(
            title=_("Open SSH Config File"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label=_("Open"),
            cancel_label=_("Cancel")
        )

        def on_file_chooser_response(dlg, response_id):
            if response_id == Gtk.ResponseType.ACCEPT:
                file = dlg.get_file()
                if file:
                    self.parser.config_path = Path(file.get_path())
                    self._load_config()
            dlg.destroy()

        dialog.connect("response", on_file_chooser_response)
        dialog.show()

    def _on_reload(self, action, param):
        """Handle reload action."""
        self._load_config()
    
    def _on_preferences(self, action, param):
        """Handle preferences action."""
        from .preferences_dialog import PreferencesDialog

        dialog = PreferencesDialog(self)

        current_prefs = {
            "config_path": str(self.parser.config_path) if self.parser else "",
            "backup_dir": str(getattr(self.parser, "backup_dir", "") or ""),
            "auto_backup": bool(getattr(self.parser, "auto_backup_enabled", True)),
            "editor_font_size": getattr(self, "_editor_font_size", 12),
            "prefer_dark_theme": getattr(self, "_prefer_dark_theme", False),
        }
        dialog.set_preferences(current_prefs)

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.OK:
                prefs = dlg.get_preferences()
                if self.parser:
                    if prefs.get("config_path"):
                        self.parser.config_path = Path(prefs["config_path"]) 
                    self.parser.auto_backup_enabled = bool(prefs.get("auto_backup", True))
                    backup_dir_val = prefs.get("backup_dir") or None
                    self.parser.backup_dir = Path(backup_dir_val).expanduser() if backup_dir_val else None
                font_size = int(prefs.get("editor_font_size") or 12)
                self._editor_font_size = font_size
                try:
                    provider = Gtk.CssProvider()
                    provider.load_from_data(f".editor-pane textview {{font-size: {font_size}pt;}}".encode())
                    Gtk.StyleContext.add_provider_for_display(
                        Gtk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                except Exception:
                    pass
                prefer_dark = bool(prefs.get("prefer_dark_theme", False))
                self._prefer_dark_theme = prefer_dark
                try:
                    style_manager = Adw.StyleManager.get_default()
                    if style_manager is not None:
                        style_manager.set_color_scheme(
                            Adw.ColorScheme.PREFER_DARK if prefer_dark else Adw.ColorScheme.DEFAULT
                        )
                except Exception:
                    pass
                if self.parser:
                    self._load_config()
                self._update_status(_("Preferences saved"))
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_about(self, action, param):
        """Show the about dialog using Adwaita's AboutWindow."""
        about_window = Adw.AboutWindow(
            transient_for=self,
            application_name=_("SSH Config Studio"),
            application_icon="com.sshconfigstudio.app",
            version="1.0.0",
            developer_name=_("Made with ❤️ by Mahyar Darvishi"),
            website="https://github.com/BuddySirJava/ssh-config-studio",
            issue_url="https://github.com/BuddySirJava/ssh-config-studio/issues",
            developers=["Mahyar Darvishi"],
            copyright=_("© 2025 Mahyar Darvishi"),
            license_type=Gtk.License.MIT_X11,
            comments=_("A native Python + GTK application for managing SSH configuration files"),
        )
        
        try:
            texture = Gdk.Texture.new_from_resource("/com/sshconfigstudio/app/media/icon_256.png")
            about_window.set_logo(texture)
        except Exception:
            pass
        about_window.set_debug_info(f"""
SSH Config Studio {about_window.get_version()}
GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}
Adwaita {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}
Python {sys.version}
        """.strip())
        
        about_window.present()

    def _update_status(self, message: str):
        """Update the status bar with a message."""
        self.show_toast(message)
    
    def _hide_status(self):
        """Hide the status bar."""
        return False
    
    def _show_error(self, message: str):
        """Show an error message in the status bar."""
        self.show_toast(message)
    
    def _show_warning(self, title: str, message: str):
        """Show a warning dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text=title,
            secondary_text=message
        )
        dialog.present()
