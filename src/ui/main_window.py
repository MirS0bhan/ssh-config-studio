"""Main Window: Primary interface for SSH Config Studio."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib, Pango, GdkPixbuf, Gdk
from pathlib import Path

from .host_list import HostList
from .host_editor import HostEditor
from .search_bar import SearchBar

class MainWindow(Gtk.ApplicationWindow):
    """Main application window for SSH Config Studio."""
    
    def __init__(self, app):
        super().__init__(
            application=app,
            title="SSH Config Studio",
            default_width=1200,
            default_height=800
        )
        
        self.app = app
        self.parser = app.parser
        self.is_dirty = False
        
        self._setup_ui()
        self._connect_signals()
        self._load_config()
    
    def _setup_ui(self):
        """Set up the main user interface."""
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.main_box)
        
        self._setup_header_bar()
        
        self.search_bar = SearchBar()
        self.main_box.append(self.search_bar)
        
        self._setup_split_view()
        
        self._setup_status_bar()
    
    def _setup_header_bar(self):
        """Set up the header bar with title, search, and actions."""
        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)
        
        title_label = Gtk.Label(label="SSH Config Studio")
        title_label.add_css_class("title")
        header_bar.set_title_widget(title_label)
        
        search_button = Gtk.Button()
        search_button.set_icon_name("system-search-symbolic")
        search_button.connect("clicked", self._on_search_clicked)
        search_button.set_tooltip_text("Search (Ctrl+F)")
        header_bar.pack_start(search_button)
        
        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._on_save_clicked)
        self.save_button.set_sensitive(False)
        header_bar.pack_end(self.save_button)
        
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu_model())
        header_bar.pack_end(menu_button)
    
    def _create_menu_model(self):
        """Create the application menu model."""
        menu = Gio.Menu()
        
        file_section = Gio.Menu()
        file_section.append("Open Config", "app.open-config")
        file_section.append("Reload", "app.reload")
        file_section.append("Preferences", "app.preferences")
        menu.append_section("File", file_section)
        
        help_section = Gio.Menu()
        help_section.append("About", "app.about")
        menu.append_section("Help", help_section)
        
        return menu
    
    def _setup_status_bar(self):
        """Set up the status bar for displaying messages."""
        self.status_bar = Gtk.InfoBar()
        self.status_bar.set_revealed(False)
        self.main_box.append(self.status_bar)
        
        self.status_label = Gtk.Label()
        self.status_bar.add_child(self.status_label)
        
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda w: self.status_bar.set_revealed(False))
        self.status_bar.add_action_widget(close_button, Gtk.ResponseType.CLOSE)
    
    def _setup_split_view(self):
        """Set up the split view between host list and editor."""
        self.host_list = HostList()
        self.host_editor = HostEditor(self.app)
        
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(self.host_list)
        paned.set_end_child(self.host_editor)
        paned.set_position(400)
        
        self.main_box.append(paned)
    
    def _connect_signals(self):
        """Connect all the signal handlers."""
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
        
        self.insert_action_group("app", actions)
    
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
    
    def _on_search_clicked(self, button):
        """Handle search button click."""
        self.search_bar.grab_focus()
    
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
            self.parser.parse() # Re-parse to get a fresh 'original_lines' for dirty check
            # Reload hosts in the list to ensure the UI references the fresh list instance
            self.host_list.load_hosts(self.parser.config.hosts)
            self.is_dirty = False
            self.save_button.set_sensitive(False)
            self._update_status("Configuration saved successfully")
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
            self._update_status("Host added")
            self.host_editor.set_visible(True)
            self.host_editor.load_host(host)
    
    def _on_host_deleted(self, host_list, host):
        """Handle host deletion."""
        if self.parser:
            self.parser.config.remove_host(host)
            self.is_dirty = True
            self.save_button.set_sensitive(True)
            self._update_status("Host deleted")
            
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
            title="Open SSH Config File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Open",
            cancel_label="Cancel"
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

        # Pre-fill from current state
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
                # Preferences are handled directly here
                prefs = dlg.get_preferences()
                # Apply parser preferences
                if self.parser:
                    if prefs.get("config_path"):
                        self.parser.config_path = Path(prefs["config_path"]) 
                    self.parser.auto_backup_enabled = bool(prefs.get("auto_backup", True))
                    backup_dir_val = prefs.get("backup_dir") or None
                    self.parser.backup_dir = Path(backup_dir_val).expanduser() if backup_dir_val else None
                # Apply editor font size
                font_size = int(prefs.get("editor_font_size") or 12)
                self._editor_font_size = font_size
                try:
                    provider = Gtk.CssProvider()
                    provider.load_from_data(f".editor-pane textview {{font-size: {font_size}pt;}}".encode())
                    Gtk.StyleContext.add_provider_for_display(
                        Gtk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                except Exception:
                    # Ignore if CSS application fails
                    pass
                # Apply dark theme preference
                prefer_dark = bool(prefs.get("prefer_dark_theme", False))
                self._prefer_dark_theme = prefer_dark
                try:
                    settings = Gtk.Settings.get_default()
                    if settings is not None and hasattr(settings, 'set_property'):
                        settings.set_property("gtk-application-prefer-dark-theme", prefer_dark)
                except Exception:
                    # Ignore if theme setting fails
                    pass
                # Reload config if path changed
                if self.parser:
                    self._load_config()
                self._update_status("Preferences saved")
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(
            transient_for=self,
            program_name="SSH Config Studio",
            version="1.0.0",
            comments="A native Python + GTK application for managing SSH configuration files",
            website="https://github.com/BuddySirJava/ssh-config-studio",
            website_label="GitHub Repository",
            copyright="Made with ❤️ by Mahyar Darvishi",
            license_type=Gtk.License.MIT_X11,
            logo=Gdk.Texture.new_for_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size("ui/assets/icon.png", 128, 128))
        )
        about_dialog.present()

        def _post_present():
            try:
                self._disable_label_selection(about_dialog)
                # Try to focus a button (e.g., Close) to avoid any label getting focus/selection.
                self._focus_first_button(about_dialog)
            except Exception:
                # Ignore if focusing button fails.
                pass
            return False

        GLib.idle_add(_post_present)

    def _disable_label_selection(self, root_widget: Gtk.Widget):
        """Recursively disable selection on all labels within a widget tree."""
        try:
            if isinstance(root_widget, Gtk.Label):
                try:
                    root_widget.set_selectable(False)
                except Exception:
                    # Ignore if setting selectable fails.
                    pass
                try:
                    # Clear any existing selection.
                    root_widget.select_region(0, 0)
                except Exception:
                    # Ignore if clearing selection fails.
                    pass

            child = root_widget.get_first_child()
            while child is not None:
                self._disable_label_selection(child)
                child = child.get_next_sibling()
        except Exception:
            # Ignore if recursion fails.
            pass

    def _focus_first_button(self, root_widget: Gtk.Widget) -> bool:
        """Recursively find the first button in the widget tree and focus it."""
        try:
            if isinstance(root_widget, Gtk.Button):
                try:
                    root_widget.grab_focus()
                    return True
                except Exception:
                    return False

            child = root_widget.get_first_child()
            while child is not None:
                if self._focus_first_button(child):
                    return True
                child = child.get_next_sibling()
        except Exception:
            return False
        return False
    
    def _update_status(self, message: str):
        """Update the status bar with a message."""
        self.status_label.set_text(message)
        self.status_bar.set_revealed(True)
        
        GLib.timeout_add_seconds(3, self._hide_status)
    
    def _hide_status(self):
        """Hide the status bar."""
        self.status_bar.set_revealed(False)
        return False
    
    def _show_error(self, message: str):
        """Show an error message in the status bar."""
        self.status_bar.set_message_type(Gtk.MessageType.ERROR)
        self._update_status(message)
    
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
