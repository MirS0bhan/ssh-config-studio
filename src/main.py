#!/usr/bin/env python3
"""SSH Config Studio: Main Application Entry Point."""

import sys
import gi
import logging
from pathlib import Path

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib

from ssh_config_parser import SSHConfigParser
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SSHConfigStudioApp(Gtk.Application):
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
        if not self.main_window:
            self.main_window = MainWindow(self)
            self.main_window.present()
        else:
            self.main_window.present()
    
    def do_startup(self):
        """Application startup handler."""
        Gtk.Application.do_startup(self)
        
        try:
            self.parser = SSHConfigParser()
            self.parser.parse()
        except Exception as e:
            logging.error(f"Failed to initialize SSH config parser: {e}")
            self._show_error_dialog("Failed to load SSH config", str(e))
    
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
        self._show_error_dialog("Error", message)

    def _show_toast(self, message: str):
        """Displays a transient toast message to the user."""
        logging.info(f"Toast: {message}")
        if self.main_window:
            # Reuse the main window's status bar for toast messages
            self.main_window.status_bar.set_message_type(Gtk.MessageType.INFO)
            self.main_window._update_status(message)

def main():
    app = SSHConfigStudioApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
