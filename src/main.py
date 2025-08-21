#!/usr/bin/env python3
"""SSH Config Studio: Main Application Entry Point."""

import sys
import gi
import logging
from pathlib import Path
from gettext import gettext as _
import gettext

import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, GLib, Gdk, Adw

# Import from installed package name if available, fallback to local
try:
    from ssh_config_studio.ssh_config_parser import SSHConfigParser
except ImportError:
    from ssh_config_parser import SSHConfigParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SSHConfigStudioApp(Adw.Application):
    """Main application class for SSH Config Studio."""
    
    def __init__(self):
        super().__init__(
            application_id="com.sshconfigstudio.app",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.parser = None
        self.main_window = None
        
    def do_activate(self):
        """Application activation handler."""
        # Import UI lazily so GResource is already registered in do_startup
        try:
            from ssh_config_studio.ui.main_window import MainWindow
        except ImportError:
            from ui.main_window import MainWindow
        
        if not self.main_window:
            self.main_window = MainWindow(self)
            self.main_window.present()
        else:
            self.main_window.present()
    
    def do_startup(self):
        """Application startup handler."""
        Adw.Application.do_startup(self)

        # Initialize gettext domain (installed to share/locale)
        try:
            locale_dir = os.path.join(GLib.get_user_data_dir(), 'locale')
            gettext.bindtextdomain('ssh-config-studio', locale_dir)
            gettext.textdomain('ssh-config-studio')
        except Exception:
            # Continue without i18n if binding fails
            pass

        self._load_css_styles()

        # Ensure our resources are available in various environments (Flatpak, installed, dev)
        resource_candidates = [
            os.path.join(GLib.get_user_data_dir(), 'com.sshconfigstudio.app', 'ssh-config-studio-resources.gresource'),
            os.path.join(GLib.get_user_data_dir(), 'ssh-config-studio-resources.gresource'),
            '/app/share/com.sshconfigstudio.app/ssh-config-studio-resources.gresource',
            '/app/share/ssh-config-studio-resources.gresource',
            os.path.join(GLib.get_home_dir(), '.local', 'share', 'com.sshconfigstudio.app', 'ssh-config-studio-resources.gresource'),
            'data/ssh-config-studio-resources.gresource',
        ]
        for candidate in resource_candidates:
            try:
                if os.path.exists(candidate):
                    resource = Gio.Resource.load(candidate)
                    Gio.resources_register(resource)
                    break
            except Exception:
                continue
        
        try:
            self.parser = SSHConfigParser()
            self.parser.parse()
        except Exception as e:
            logging.error(f"Failed to initialize SSH config parser: {e}")
            self._show_error_dialog(_("Failed to load SSH config"), str(e))
    
    def _load_css_styles(self):
        """Load application CSS styles."""
        try:
            # Try to load CSS from various locations
            css_candidates = [
                os.path.join(GLib.get_user_data_dir(), 'com.sshconfigstudio.app', 'ssh-config-studio.css'),
                os.path.join(GLib.get_user_data_dir(), 'ssh-config-studio.css'),
                '/app/share/com.sshconfigstudio.app/ssh-config-studio.css',
                '/app/share/ssh-config-studio.css',
                os.path.join(GLib.get_home_dir(), '.local', 'share', 'com.sshconfigstudio.app', 'ssh-config-studio.css'),
                'data/ssh-config-studio.css',
            ]
            
            for candidate in css_candidates:
                if os.path.exists(candidate):
                    try:
                        css_provider = Gtk.CssProvider()
                        css_provider.load_from_path(candidate)
                        Gtk.StyleContext.add_provider_for_display(
                            Gdk.Display.get_default(),
                            css_provider,
                            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                        )
                        logging.info(f"Loaded CSS styles from: {candidate}")
                        break
                    except Exception as e:
                        logging.warning(f"Failed to load CSS from {candidate}: {e}")
                        continue
        except Exception as e:
            logging.warning(f"Failed to load CSS styles: {e}")
    
    def _show_error_dialog(self, title: str, message: str):
        """Show an error dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.main_window, # Set the main window as the transient parent
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
            secondary_text=message
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()

    def _show_error(self, message: str):
        """Displays an error message to the user, typically from HostEditor or other components."""
        logging.error(f"Application Error: {message}")
        # Reuse the existing error dialog logic
        self._show_error_dialog(_("Error"), message)

    def _show_toast(self, message: str):
        """Displays a transient toast message to the user."""
        logging.info(f"Toast: {message}")
        if self.main_window and hasattr(self.main_window, "show_toast"):
            try:
                self.main_window.show_toast(message)
                return
            except Exception:
                pass
        # Fallback: message dialog if toast overlay is unavailable
        self._show_error_dialog(_("Info"), message)

def main():
    app = SSHConfigStudioApp()
    try:
        app.set_default_icon_name('com.sshconfigstudio.app')
    except Exception:
        # Icon is optional in some environments
        pass
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
