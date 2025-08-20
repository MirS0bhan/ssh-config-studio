
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, GLib

class SearchBar(Gtk.Box):
    
    # Custom signals
    __gsignals__ = {
        'search-changed': (GObject.SignalFlags.RUN_LAST, None, (str,))
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.search_timeout = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        search_icon = Gtk.Image()
        search_icon.set_from_icon_name("system-search-symbolic")
        search_icon.set_margin_start(12)
        self.append(search_icon)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search hosts, hostnames, users, keys...")
        self.search_entry.set_tooltip_text("Search across all SSH host configurations")
        self.search_entry.set_margin_start(6)
        self.search_entry.set_margin_end(12)
        self.search_entry.set_margin_top(6)
        self.search_entry.set_margin_bottom(6)
        self.append(self.search_entry)

        self.clear_button = Gtk.Button()
        self.clear_button.set_icon_name("edit-clear-symbolic")
        self.clear_button.set_tooltip_text("Clear search")
        self.clear_button.connect("clicked", self._on_clear_clicked)
        self.clear_button.set_visible(False)
        self.append(self.clear_button)

        self.add_css_class("search-bar")
        self.search_entry.add_css_class("search-entry")

    def _connect_signals(self):
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("changed", self._on_text_changed)

    def _on_search_changed(self, entry):
        query = entry.get_text()
        self._update_clear_button(query)

        if self.search_timeout:
            GLib.source_remove(self.search_timeout)

        self.search_timeout = GLib.timeout_add(300, self._perform_search, query)

    def _on_text_changed(self, entry):
        query = entry.get_text()
        self._update_clear_button(query)

    def _on_clear_clicked(self, button):
        self.search_entry.set_text("")
        self.search_entry.grab_focus()

    def _update_clear_button(self, query: str):
        has_text = bool(query.strip())
        self.clear_button.set_visible(has_text)

    def _perform_search(self, query: str):
        self.emit("search-changed", query)
        self.search_timeout = None
        return False

    def get_search_text(self) -> str:
        return self.search_entry.get_text()

    def set_search_text(self, text: str):
        self.search_entry.set_text(text)

    def clear_search(self):
        self.search_entry.set_text("")

    def grab_focus(self):
        self.search_entry.grab_focus()
