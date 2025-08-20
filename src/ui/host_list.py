"""
Host List - Component for displaying and managing SSH hosts.

This module provides a list view of SSH hosts with search, add, duplicate,
and delete functionality.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango

from ssh_config_parser import SSHHost, SSHOption

class HostList(Gtk.Box):
    
    # Custom signals
    __gsignals__ = {
        'host-selected': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'host-added': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'host-deleted': (GObject.SignalFlags.RUN_LAST, None, (object,))
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.hosts = []
        self.filtered_hosts = []
        self.current_filter = ""
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.add_css_class("host-list-header")
        header_box.set_hexpand(True)

        title_label = Gtk.Label(label="SSH Hosts")
        title_label.add_css_class("title")
        title_label.set_xalign(0)
        header_box.append(title_label)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.add_css_class("linked")

        add_button = Gtk.Button()
        add_button.set_icon_name("list-add-symbolic")
        add_button.set_tooltip_text("Add Host")
        add_button.connect("clicked", self._on_add_clicked)
        button_box.append(add_button)

        duplicate_button = Gtk.Button()
        duplicate_button.set_icon_name("edit-copy-symbolic")
        duplicate_button.set_tooltip_text("Duplicate Host")
        duplicate_button.connect("clicked", self._on_duplicate_clicked)
        button_box.append(duplicate_button)

        delete_button = Gtk.Button()
        delete_button.set_icon_name("edit-delete-symbolic")
        delete_button.set_tooltip_text("Delete Host")
        delete_button.connect("clicked", self._on_delete_clicked)
        button_box.append(delete_button)

        header_box.append(button_box)
        self.append(header_box)

        self.count_label = Gtk.Label(label="0 hosts")
        self.count_label.add_css_class("dim-label")
        header_box.append(self.count_label)

        self._setup_tree_view()

        self.add_button = add_button
        self.duplicate_button = duplicate_button
        self.delete_button = delete_button

    def _setup_tree_view(self):
        self.tree_view = Gtk.TreeView()
        self.tree_view.set_headers_visible(True)
        self.tree_view.set_search_column(0)
        self.tree_view.set_hexpand(True)
        self.tree_view.set_vexpand(True)

        self.list_store = Gtk.ListStore(str, str, str, str, str, object)
        self.tree_view.set_model(self.list_store)

        self._setup_columns()

        selection = self.tree_view.get_selection()
        selection.connect("changed", self._on_selection_changed)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.tree_view)
        scrolled_window.set_min_content_width(350)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        self.append(scrolled_window)

    def _setup_columns(self):
        def add_text_column(title: str, col_index: int, expand: bool = False, min_width: int | None = None):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ypad", 6)
            renderer.set_property("xpad", 8)
            column = Gtk.TreeViewColumn(title, renderer, text=col_index)
            if expand:
                column.set_expand(True)
            if min_width is not None:
                column.set_min_width(min_width)
            self.tree_view.append_column(column)

        add_text_column("Host", 0, True, 120)
        add_text_column("HostName", 1, True, 150)
        add_text_column("User", 2, False, 80)
        add_text_column("Port", 3, False, 60)
        add_text_column("Identity", 4, True, 120)
        
    def _connect_signals(self): # type: ignore[empty-body]
        pass # No signals specific to HostList itself, handled by parent/children

    def load_hosts(self, hosts: list):
        self.hosts = hosts
        self.filtered_hosts = hosts.copy()
        self._refresh_view()
        self._update_count()

    def filter_hosts(self, query: str):
        self.current_filter = query.lower()

        if not query:
            self.filtered_hosts = self.hosts.copy()
        else:
            self.filtered_hosts = []
            for host in self.hosts:
                searchable_text = (
                    " ".join(host.patterns) + " " +
                    (host.get_option('HostName') or "") + " " +
                    (host.get_option('User') or "") + " " +
                    (host.get_option('IdentityFile') or "")
                ).lower()

                if query.lower() in searchable_text:
                    self.filtered_hosts.append(host)

        self._refresh_view()
        self._update_count()

    def _refresh_view(self):
        selection = self.tree_view.get_selection()
        model, selected_iter = selection.get_selected()
        previously_selected_host = None
        if selected_iter:
            previously_selected_host = model.get_value(selected_iter, 5)

        self.list_store.clear()

        for host in self.filtered_hosts:
            host_patterns = ", ".join(host.patterns)
            hostname = host.get_option('HostName') or ""
            user = host.get_option('User') or ""
            port = host.get_option('Port') or ""
            identity_file = host.get_option('IdentityFile') or ""

            self.list_store.append([
                host_patterns,
                hostname,
                user,
                port,
                identity_file,
                host
            ])

        if previously_selected_host:
            self.select_host(previously_selected_host)

    def _update_count(self):
        total = len(self.hosts)
        filtered = len(self.filtered_hosts)

        if filtered == total:
            self.count_label.set_text(f"{total} hosts")
        else:
            self.count_label.set_text(f"{filtered} of {total} hosts")

    def _on_selection_changed(self, selection):
        model, tree_iter = selection.get_selected()
        if tree_iter:
            host = model.get_value(tree_iter, 5)
            self.emit("host-selected", host)

            self.duplicate_button.set_sensitive(True)
            self.delete_button.set_sensitive(True)
        else:
            self.duplicate_button.set_sensitive(False)
            self.delete_button.set_sensitive(False)

    def _on_add_clicked(self, button):
        new_host = SSHHost(patterns=["new-host"])
        # Emit the signal so the main window can finalize and add to the shared config list.
        # This avoids double-appending as self.hosts references the parser's config.hosts.
        self.emit("host-added", new_host)

        # Recompute filtered view from the updated shared list.
        self.filter_hosts(self.current_filter)

        self.select_host(new_host)

    def _on_duplicate_clicked(self, button):
        selection = self.tree_view.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter:
            original_host = model.get_value(tree_iter, 5)
            duplicated_host = self._duplicate_host(original_host)

            # Let the main window add it to the shared config list.
            self.emit("host-added", duplicated_host)

            # Refresh view from the shared list after addition.
            self.filter_hosts(self.current_filter)

            self.select_host(duplicated_host)

    def _on_delete_clicked(self, button):
        selection = self.tree_view.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter:
            host = model.get_value(tree_iter, 5)

            dialog = Gtk.MessageDialog(
                transient_for=self.get_root(),
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=f"Delete host '{', '.join(host.patterns)}'?",
            )
            dialog.add_buttons(
                "No", Gtk.ResponseType.NO,
                "Yes", Gtk.ResponseType.YES,
            )

            def on_response(dlg, response_id):
                if response_id == Gtk.ResponseType.YES:
                    self.emit("host-deleted", host)
                    if host in self.hosts:
                        self.hosts.remove(host)
                    if host in self.filtered_hosts:
                        self.filtered_hosts.remove(host)
                    self._refresh_view()
                    self._update_count()
                dlg.destroy()

            dialog.connect("response", on_response)
            dialog.present()

    def _duplicate_host(self, original_host: SSHHost) -> SSHHost:
        duplicated_host = SSHHost()

        duplicated_host.patterns = [f"{pattern}-copy" for pattern in original_host.patterns]

        for option in original_host.options:
            duplicated_option = SSHOption(
                key=option.key,
                value=option.value,
                indentation=option.indentation
            )
            duplicated_host.options.append(duplicated_option)

        return duplicated_host

    def _host_matches_filter(self, host: SSHHost) -> bool:
        if not self.current_filter:
            return True

        searchable_text = (
            " ".join(host.patterns) + " " +
            (host.get_option('HostName') or "") + " " +
            (host.get_option('User') or "") + " " +
            (host.get_option('IdentityFile') or "")
        ).lower()

        return self.current_filter in searchable_text

    def select_host(self, host: SSHHost):
        for index, row in enumerate(self.list_store):
            if row[5] == host:
                tree_iter = self.list_store.iter_nth_child(None, index)
                if tree_iter is None:
                    return
                selection = self.tree_view.get_selection()
                selection.select_iter(tree_iter)
                path = self.list_store.get_path(tree_iter)
                if path is not None:
                    self.tree_view.scroll_to_cell(path, None, False, 0, 0)
                break
