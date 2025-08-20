"""Launcher script for SSH Config Studio."""

import sys
import gi

gi.require_version('Gtk', '4.0')
def main():
	from main import main as app_main
	return app_main()


if __name__ == "__main__":
	sys.exit(main())
