import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gio, Gdk, GLib
import subprocess
import threading

# Support both installed package and local source tree
try:
	from ssh_config_studio.ssh_config_parser import SSHHost, SSHOption
except ImportError:
	from ssh_config_parser import SSHHost, SSHOption
import difflib
import copy
from gettext import gettext as _
import os

@Gtk.Template(resource_path="/com/sshconfigstudio/app/ui/host_editor.ui")
class HostEditor(Gtk.Box):

    __gtype_name__ = "HostEditor"

    # Template children
    notebook = Gtk.Template.Child()
    patterns_entry = Gtk.Template.Child()
    patterns_error_label = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    user_entry = Gtk.Template.Child()
    port_entry = Gtk.Template.Child()
    port_error_label = Gtk.Template.Child()
    identity_entry = Gtk.Template.Child()
    identity_button = Gtk.Template.Child()
    forward_agent_switch = Gtk.Template.Child()
    proxy_jump_entry = Gtk.Template.Child()
    proxy_cmd_entry = Gtk.Template.Child()
    local_forward_entry = Gtk.Template.Child()
    remote_forward_entry = Gtk.Template.Child()
    custom_options_list = Gtk.Template.Child()
    add_custom_button = Gtk.Template.Child()
    raw_text_view = Gtk.Template.Child()
    copy_ssh_button = Gtk.Template.Child()
    test_connection_button = Gtk.Template.Child()
    revert_button = Gtk.Template.Child()

    # Custom signals
    __gsignals__ = {
        'host-changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'editor-validity-changed': (GObject.SignalFlags.RUN_LAST, None, (bool,))
    }

    def __init__(self):
        super().__init__()
        self.set_visible(False)
        self.app = None
        self.current_host = None
        self.is_loading = False
        self._programmatic_raw_update = False
        # CSS for inline validation errors
        try:
            css = Gtk.CssProvider()
            css.load_from_data(b"""
            .error-label { color: #e01b24; }
            .entry-error { border-color: #e01b24; }
            """)
            Gtk.StyleContext.add_provider_for_display(
                Gtk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            pass
        self._connect_signals()
        try:
            self.buffer = self.raw_text_view.get_buffer()
            self.tag_add = self.buffer.create_tag("added", background="#aaffaa", foreground="black")
            self.tag_removed = self.buffer.create_tag("removed", background="#ffaaaa", foreground="black")
            self.tag_changed = self.buffer.create_tag("changed", background="#ffffaa", foreground="black")
        except Exception:
            self.buffer = None
            self.tag_add = None
            self.tag_removed = None
            self.tag_changed = None

    def set_app(self, app):
        self.app = app

    def _setup_ui(self):
        title_label = Gtk.Label(label="Host Configuration")
        title_label.add_css_class("title")
        self.append(title_label)
        
        self.notebook = Gtk.Notebook()
        self.append(self.notebook)
        
        self._setup_basic_tab()
        
        self._setup_networking_tab()
        
        self._setup_advanced_tab()
        
        self._setup_raw_tab()
        
        self._setup_quick_actions()
    
    def _setup_basic_tab(self):
        basic_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        basic_box.set_margin_start(12)
        basic_box.set_margin_end(12)
        basic_box.set_margin_top(12)
        basic_box.set_margin_bottom(12)
        
        patterns_label = Gtk.Label(label="Host Patterns:")
        patterns_label.set_xalign(0)
        basic_box.append(patterns_label)
        
        self.patterns_entry = Gtk.Entry()
        self.patterns_entry.set_placeholder_text("host1 host2 host3")
        self.patterns_entry.set_tooltip_text("Space-separated host patterns")
        basic_box.append(self.patterns_entry)
        self.patterns_error_label = Gtk.Label()
        self.patterns_error_label.set_xalign(0)
        self.patterns_error_label.add_css_class("error-label")
        self.patterns_error_label.set_visible(False)
        basic_box.append(self.patterns_error_label)
        
        hostname_label = Gtk.Label(label="HostName:")
        hostname_label.set_xalign(0)
        hostname_label.set_margin_top(12)
        basic_box.append(hostname_label)
        
        self.hostname_entry = Gtk.Entry()
        self.hostname_entry.set_placeholder_text("example.com")
        basic_box.append(self.hostname_entry)
        
        user_label = Gtk.Label(label="User:")
        user_label.set_xalign(0)
        user_label.set_margin_top(12)
        basic_box.append(user_label)
        
        self.user_entry = Gtk.Entry()
        self.user_entry.set_placeholder_text("username")
        basic_box.append(self.user_entry)
        
        port_label = Gtk.Label(label="Port:")
        port_label.set_xalign(0)
        port_label.set_margin_top(12)
        basic_box.append(port_label)
        
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("22")
        basic_box.append(self.port_entry)
        self.port_error_label = Gtk.Label()
        self.port_error_label.set_xalign(0)
        self.port_error_label.add_css_class("error-label")
        self.port_error_label.set_visible(False)
        basic_box.append(self.port_error_label)
        
        identity_label = Gtk.Label(label="Identity File:")
        identity_label.set_xalign(0)
        identity_label.set_margin_top(12)
        basic_box.append(identity_label)
        
        identity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.identity_entry = Gtk.Entry()
        self.identity_entry.set_placeholder_text("~/.ssh/id_rsa")
        identity_box.append(self.identity_entry)
        
        identity_button = Gtk.Button()
        identity_button.set_icon_name("document-open-symbolic")
        identity_button.set_tooltip_text("Choose Identity File")
        identity_button.connect("clicked", self._on_identity_file_clicked)
        identity_box.append(identity_button)
        
        basic_box.append(identity_box)
        
        forward_agent_label = Gtk.Label(label="Forward Agent:")
        forward_agent_label.set_xalign(0)
        forward_agent_label.set_margin_top(12)
        basic_box.append(forward_agent_label)
        
        self.forward_agent_switch = Gtk.Switch()
        self.forward_agent_switch.set_valign(Gtk.Align.CENTER)
        self.forward_agent_switch.set_halign(Gtk.Align.START)
        self.forward_agent_switch.set_hexpand(False)
        basic_box.append(self.forward_agent_switch)
        
        self.notebook.append_page(basic_box, Gtk.Label(label="Basic"))
    
    def _setup_networking_tab(self):
        networking_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        networking_box.set_margin_start(12)
        networking_box.set_margin_end(12)
        networking_box.set_margin_top(12)
        networking_box.set_margin_bottom(12)
        
        proxy_jump_label = Gtk.Label(label="ProxyJump:")
        proxy_jump_label.set_xalign(0)
        networking_box.append(proxy_jump_label)
        
        self.proxy_jump_entry = Gtk.Entry()
        self.proxy_jump_entry.set_placeholder_text("user@jump-host")
        networking_box.append(self.proxy_jump_entry)
        
        proxy_cmd_label = Gtk.Label(label="ProxyCommand:")
        proxy_cmd_label.set_xalign(0)
        proxy_cmd_label.set_margin_top(12)
        networking_box.append(proxy_cmd_label)
        
        self.proxy_cmd_entry = Gtk.Entry()
        self.proxy_cmd_entry.set_placeholder_text("ssh -W %h:%p user@jump-host")
        networking_box.append(self.proxy_cmd_entry)
        
        local_forward_label = Gtk.Label(label="Local Forward:")
        local_forward_label.set_xalign(0)
        local_forward_label.set_margin_top(12)
        networking_box.append(local_forward_label)
        
        self.local_forward_entry = Gtk.Entry()
        self.local_forward_entry.set_placeholder_text("8080:localhost:80")
        networking_box.append(self.local_forward_entry)
        
        remote_forward_label = Gtk.Label(label="Remote Forward:")
        remote_forward_label.set_xalign(0)
        remote_forward_label.set_margin_top(12)
        networking_box.append(remote_forward_label)
        
        self.remote_forward_entry = Gtk.Entry()
        self.remote_forward_entry.set_placeholder_text("8080:localhost:80")
        networking_box.append(self.remote_forward_entry)
        
        self.notebook.append_page(networking_box, Gtk.Label(label="Networking"))
    
    def _setup_advanced_tab(self):
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        advanced_box.set_margin_start(12)
        advanced_box.set_margin_end(12)
        advanced_box.set_margin_top(12)
        advanced_box.set_margin_bottom(12)
        
        custom_label = Gtk.Label(label="Custom Options:")
        custom_label.set_xalign(0)
        advanced_box.append(custom_label)
        
        self.custom_options_list = Gtk.ListBox()
        self.custom_options_list.set_selection_mode(Gtk.SelectionMode.NONE)
        advanced_box.append(self.custom_options_list)
        
        add_custom_button = Gtk.Button(label="Add Custom Option")
        add_custom_button.connect("clicked", self._on_add_custom_option)
        advanced_box.append(add_custom_button)
        
        self.notebook.append_page(advanced_box, Gtk.Label(label="Advanced"))
    
    def _setup_raw_tab(self):
        raw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        raw_box.set_margin_start(12)
        raw_box.set_margin_end(12)
        raw_box.set_margin_top(12)
        raw_box.set_margin_bottom(12)
        
        raw_label = Gtk.Label(label="Raw Configuration:")
        raw_label.set_xalign(0)
        raw_box.append(raw_label)
        
        self.raw_text_view = Gtk.TextView()
        self.raw_text_view.set_monospace(True)
        self.raw_text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.raw_text_view.set_editable(True)
        self.raw_text_view.set_hexpand(True)
        self.raw_text_view.set_vexpand(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.raw_text_view)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        raw_box.append(scrolled_window)
        
        self.notebook.append_page(raw_box, Gtk.Label(label="Raw/Diff"))

    def _setup_quick_actions(self):
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        actions_box.add_css_class("linked")
        actions_box.set_margin_start(12)
        actions_box.set_margin_end(12)
        actions_box.set_margin_top(12)
        actions_box.set_margin_bottom(12)
        
        copy_ssh_button = Gtk.Button(label="Copy SSH Command")
        copy_ssh_button.connect("clicked", self._on_copy_ssh_command)
        actions_box.append(copy_ssh_button)
        
        test_connection_button = Gtk.Button(label="Test Connection")
        test_connection_button.connect("clicked", self._on_test_connection)
        actions_box.append(test_connection_button)

        self.revert_button = Gtk.Button(label="Revert")
        self.revert_button.add_css_class("destructive-action")
        self.revert_button.connect("clicked", self._on_revert_clicked)
        self.revert_button.set_sensitive(False) # Initially insensitive
        actions_box.append(self.revert_button)
        
        self.append(actions_box)
    
    def _connect_signals(self):
        self.patterns_entry.connect("changed", self._on_field_changed)
        self.hostname_entry.connect("changed", self._on_field_changed)
        self.user_entry.connect("changed", self._on_field_changed)
        self.port_entry.connect("changed", self._on_field_changed)
        self.identity_entry.connect("changed", self._on_field_changed)
        self.forward_agent_switch.connect("state-set", self._on_field_changed)
        
        self.proxy_jump_entry.connect("changed", self._on_field_changed)
        self.proxy_cmd_entry.connect("changed", self._on_field_changed)
        self.local_forward_entry.connect("changed", self._on_field_changed)
        self.remote_forward_entry.connect("changed", self._on_field_changed)
        
        self._raw_changed_handler_id = self.raw_text_view.get_buffer().connect("changed", self._on_raw_text_changed)

        # Connect buttons (explicitly, as they are not tied to field changes directly)
        self.identity_button.connect("clicked", self._on_identity_file_clicked)
        self.add_custom_button.connect("clicked", self._on_add_custom_option)
        self.copy_ssh_button.connect("clicked", self._on_copy_ssh_command)
        self.test_connection_button.connect("clicked", self._on_test_connection)
        self.revert_button.connect("clicked", self._on_revert_clicked)
    
    def load_host(self, host: SSHHost):
        self.is_loading = True
        self.current_host = host
        self.original_host_state = copy.deepcopy(host)
        
        if not host:
            self._clear_all_fields()
            self.is_loading = False
            return
        
        self.patterns_entry.set_text(" ".join(host.patterns))
        self.hostname_entry.set_text(host.get_option('HostName') or "")
        self.user_entry.set_text(host.get_option('User') or "")
        self.port_entry.set_text(host.get_option('Port') or "")
        self.identity_entry.set_text(host.get_option('IdentityFile') or "")
        
        forward_agent = host.get_option('ForwardAgent')
        self.forward_agent_switch.set_active(forward_agent == 'yes')
        
        self.proxy_jump_entry.set_text(host.get_option('ProxyJump') or "")
        self.proxy_cmd_entry.set_text(host.get_option('ProxyCommand') or "")
        self.local_forward_entry.set_text(host.get_option('LocalForward') or "")
        self.remote_forward_entry.set_text(host.get_option('RemoteForward') or "")
        
        self._load_custom_options(host)

        self.raw_text_view.get_buffer().set_text("\n".join(host.raw_lines))
        self.original_raw_content = "\n".join(host.raw_lines)
        
        self.is_loading = False
        self.revert_button.set_sensitive(False)

        self._programmatic_raw_update = True
        try:
            self._on_raw_text_changed(self.raw_text_view.get_buffer())
        finally:
            self._programmatic_raw_update = False
    
    def _clear_all_fields(self):
        """Clears all input fields and custom options."""
        self.patterns_entry.set_text("")
        self.hostname_entry.set_text("")
        self.user_entry.set_text("")
        self.port_entry.set_text("")
        self.identity_entry.set_text("")
        self.forward_agent_switch.set_active(False)
        self.proxy_jump_entry.set_text("")
        self.proxy_cmd_entry.set_text("")
        self.local_forward_entry.set_text("")
        self.remote_forward_entry.set_text("")
        self._clear_custom_options()
    
    def _load_custom_options(self, host: SSHHost):
        """Loads custom SSH options into the custom options list."""
        self._clear_custom_options()
        
        common_options = {
            'HostName', 'User', 'Port', 'IdentityFile', 'ForwardAgent',
            'ProxyJump', 'ProxyCommand', 'LocalForward', 'RemoteForward'
        }
        
        for option in host.options:
            if option.key not in common_options:
                self._add_custom_option_row(option.key, option.value)
    
    def _clear_custom_options(self):
        """Clears all custom option rows from the list."""
        while self.custom_options_list.get_first_child():
            self.custom_options_list.remove(self.custom_options_list.get_first_child())
    
    def _add_custom_option_row(self, key: str = "", value: str = ""):
        """Adds a new row for a custom option to the list."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.set_margin_top(6)
        row.set_margin_bottom(6)
        
        key_entry = Gtk.Entry()
        key_entry.set_text(key)
        key_entry.set_placeholder_text("Option")
        key_entry.set_size_request(120, -1)
        row.append(key_entry)
        
        value_entry = Gtk.Entry()
        value_entry.set_text(value)
        value_entry.set_placeholder_text("Value")
        value_entry.set_hexpand(True)
        row.append(value_entry)
        
        remove_button = Gtk.Button()
        remove_button.set_icon_name("list-remove-symbolic")
        remove_button.connect("clicked", self._on_remove_custom_option, row)
        row.append(remove_button)
        
        self.custom_options_list.append(row)
        
        key_entry.connect("changed", self._on_custom_option_changed)
        value_entry.connect("changed", self._on_custom_option_changed)
    
    def _on_field_changed(self, widget, *args):
        """Handle changes in basic and networking fields to update host and dirty state."""
        if self.is_loading or not self.current_host:
            return
        
        self.revert_button.set_sensitive(self.is_host_dirty())

        self._validate_and_update_host()
    
    def _on_custom_option_changed(self, widget, *args):
        """Handle changes in custom option fields to update host and dirty state."""
        if self.is_loading or not self.current_host:
            return

        self.revert_button.set_sensitive(self.is_host_dirty())

        self._validate_and_update_host()

    def _update_raw_text_from_host(self):
        """Updates the raw text view based on the current host's structured data."""
        if not self.current_host:
            return

        self.is_loading = True

        generated_raw_lines = self._generate_raw_lines_from_host()
        buffer = self.raw_text_view.get_buffer()
        if hasattr(self, "_raw_changed_handler_id"):
            buffer.handler_block(self._raw_changed_handler_id)
        buffer.set_text("\n".join(generated_raw_lines))
        if hasattr(self, "_raw_changed_handler_id"):
            buffer.handler_unblock(self._raw_changed_handler_id)

        self.is_loading = False

        # Next change is programmatic; don't resync form fields
        self._programmatic_raw_update = True
        self._on_raw_text_changed(self.raw_text_view.get_buffer())
        self._programmatic_raw_update = False

    def _generate_raw_lines_from_host(self) -> list[str]:
        """Generates raw lines for the current host based on its structured data."""
        lines = []
        if self.current_host:
            # Start with the Host line
            if self.current_host.patterns:
                lines.append(f"Host {' '.join(self.current_host.patterns)}")
            
            # Add all options from the current_host.options list
            for opt in self.current_host.options:
                lines.append(str(opt))
            
            # Ensure there's a blank line at the end if there were options, for readability
            if self.current_host.options and lines[-1].strip() != "":
                lines.append("")

        return lines


    def _on_raw_text_changed(self, buffer):
        """Handle changes in the raw text view, parse, validate, and apply diff highlighting."""
        if self.is_loading or not self.current_host:
            return

        current_text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        current_lines = current_text.splitlines()
        original_lines = self.original_raw_content.splitlines()

        if self.buffer is None:
            try:
                self.buffer = self.raw_text_view.get_buffer()
            except Exception:
                return
        self.buffer.remove_all_tags(self.buffer.get_start_iter(), self.buffer.get_end_iter())

        s = difflib.SequenceMatcher(None, original_lines, current_lines)

        for opcode, i1, i2, j1, j2 in s.get_opcodes():
            if opcode == 'equal':
                pass
            elif opcode == 'insert':
                for line_idx in range(j1, j2):
                    if line_idx >= len(current_lines):
                        continue
                    success, start_iter = self.buffer.get_iter_at_line(line_idx)
                    if not success:
                        continue
                    end_iter = start_iter.copy()
                    end_iter.forward_to_line_end()
                    self.buffer.apply_tag(self.tag_add, start_iter, end_iter)
            elif opcode == 'delete':
                pass
            elif opcode == 'replace':
                for line_idx in range(j1, j2):
                    if line_idx >= len(current_lines):
                        continue
                    success, start_iter = self.buffer.get_iter_at_line(line_idx)
                    if not success:
                        continue
                    end_iter = start_iter.copy()
                    end_iter.forward_to_line_end()
                    self.buffer.apply_tag(self.tag_changed, start_iter, end_iter)

        # Only parse and validate if the change was user-initiated, not programmatic
        if not self._programmatic_raw_update:
            self._parse_and_validate_raw_text(current_lines)

    def _parse_and_validate_raw_text(self, current_lines: list[str]):
        """Parses raw lines and updates current_host and UI fields if valid."""
        try:
            temp_host = SSHHost.from_raw_lines(current_lines)
            self.current_host.patterns = temp_host.patterns
            self.current_host.options = temp_host.options
            self.current_host.raw_lines = current_lines
            self.emit("host-changed", self.current_host)
            self._sync_fields_from_host()
            self.revert_button.set_sensitive(self.is_host_dirty())
        except ValueError as e:
            self.app._show_error(f"Invalid raw host configuration: {e}")
        except Exception as e:
            self.app._show_error(f"Error parsing raw host config: {e}")

    
    def _update_host_from_fields(self):
        """Updates the current host object based on GUI field values."""
        if not self.current_host:
            return
        
        patterns_text = self.patterns_entry.get_text().strip()
        if patterns_text:
            self.current_host.patterns = [p.strip() for p in patterns_text.split()]
        
        self._update_host_option('HostName', self.hostname_entry.get_text())
        self._update_host_option('User', self.user_entry.get_text())
        self._update_host_option('Port', self.port_entry.get_text())
        self._update_host_option('IdentityFile', self.identity_entry.get_text())
        
        forward_agent = "yes" if self.forward_agent_switch.get_active() else "no"
        self._update_host_option('ForwardAgent', forward_agent)
        
        self._update_host_option('ProxyJump', self.proxy_jump_entry.get_text())
        self._update_host_option('ProxyCommand', self.proxy_cmd_entry.get_text())
        self._update_host_option('LocalForward', self.local_forward_entry.get_text())
        self._update_host_option('RemoteForward', self.remote_forward_entry.get_text())
        
        self._update_custom_options()
    
    def _update_host_option(self, key: str, value: str):
        """Helper to update or remove a single SSH option on the current host."""
        if value.strip():
            self.current_host.set_option(key, value.strip())
        else:
            self.current_host.remove_option(key)
    
    def _update_custom_options(self):
        """Updates custom options on the current host based on the listbox content."""
        common_options = {
            'HostName', 'User', 'Port', 'IdentityFile', 'ForwardAgent',
            'ProxyJump', 'ProxyCommand', 'LocalForward', 'RemoteForward'
        }
        
        # Remove all existing custom options from the host object first
        self.current_host.options = [opt for opt in self.current_host.options if opt.key in common_options]
        
        for row_widget in self.custom_options_list:
            # The actual content of the ListBoxRow is our Gtk.Box
            row_content_box = row_widget.get_child()
            if row_content_box and isinstance(row_content_box, Gtk.Box):
                key_entry = row_content_box.get_first_child()
                if not key_entry: continue
                value_entry = key_entry.get_next_sibling()
                if not value_entry: continue

                # Add explicit type checking for robustness and debugging
                if not isinstance(key_entry, Gtk.Entry) or not isinstance(value_entry, Gtk.Entry):
                    continue # Skip this row if types are unexpected

                key = key_entry.get_text().strip()
                value = value_entry.get_text().strip()
                    
                if key and value:
                    self.current_host.set_option(key, value)
    
    def _on_identity_file_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Choose Identity File"),
            transient_for=self.get_root(),
            action=Gtk.FileChooserAction.OPEN
        )
        
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Open"), Gtk.ResponseType.OK)
        
        filter_text = Gtk.FileFilter()
        filter_text.set_name(_("SSH Keys"))
        filter_text.add_pattern("*.pem")
        filter_text.add_pattern("id_*")
        dialog.add_filter(filter_text)
        
        dialog.connect("response", self._on_identity_file_response)
        dialog.present()

    def _on_identity_file_response(self, dialog, response_id):
        try:
            if response_id == Gtk.ResponseType.OK:
                file = dialog.get_file()
                if file:
                    self.identity_entry.set_text(file.get_path())
        finally:
            dialog.destroy()
        
    def _on_add_custom_option(self, button):
        self._add_custom_option_row()
    
    def _on_remove_custom_option(self, button, row):
        """Handle remove custom option button click."""
        list_box_row = row.get_parent()
        if list_box_row:
            self.custom_options_list.remove(list_box_row)
        self._update_host_from_fields()
        self.emit("host-changed", self.current_host)
    
    def _on_copy_ssh_command(self, button):
        """Copy the generated SSH command to the clipboard and show a toast."""
        if not self.current_host:
            return
        
        command_parts = ["ssh"]
        
        if self.user_entry.get_text().strip():
            command_parts.append(f"-l {self.user_entry.get_text().strip()}")
        
        if self.port_entry.get_text().strip():
            command_parts.append(f"-p {self.port_entry.get_text().strip()}")
        
        if self.identity_entry.get_text().strip():
            command_parts.append(f"-i {self.identity_entry.get_text().strip()}")
        
        if self.current_host.patterns:
            command_parts.append(self.current_host.patterns[0])
        
        command = " ".join(command_parts)
        
        clipboard = Gdk.Display.get_default().get_clipboard()
        provider = Gdk.ContentProvider.new_for_bytes(
            "text/plain;charset=utf-8",
            GLib.Bytes.new(command.encode("utf-8"))
        )
        clipboard.set(provider)
        
        self.app._show_toast(_(f"SSH command copied: {command}"))

    def is_host_dirty(self) -> bool:
        """Checks if the current host has unsaved changes compared to its original loaded state."""
        if not self.current_host or not self.original_host_state:
            return False

        if sorted(self.current_host.patterns) != sorted(self.original_host_state.patterns):
            return True

        if len(self.current_host.options) != len(self.original_host_state.options):
            return True
        
        # Create dictionaries for easier comparison, ignoring indentation for logical equivalence
        current_options_dict = {opt.key.lower(): opt.value for opt in self.current_host.options}
        original_options_dict = {opt.key.lower(): opt.value for opt in self.original_host_state.options}

        if current_options_dict != original_options_dict:
            return True

        # Finally, compare the raw lines, which will catch comments and formatting changes
        # We need to make sure to strip trailing newlines for robust comparison
        current_raw_clean = [line.rstrip('\n') for line in self.current_host.raw_lines]
        original_raw_clean = [line.rstrip('\n') for line in self.original_host_state.raw_lines]

        return current_raw_clean != original_raw_clean

    def _collect_field_errors(self) -> dict:
        errors: dict[str, str] = {}
        self._clear_field_errors()

        patterns_text = self.patterns_entry.get_text().strip()
        if not patterns_text:
            errors['patterns'] = _("Host name (patterns) is required.")

        port_text = self.port_entry.get_text().strip()
        if port_text:
            try:
                port = int(port_text)
                if not (1 <= port <= 65535):
                    errors['port'] = _("Port must be between 1 and 65535.")
            except ValueError:
                errors['port'] = _("Port must be numeric.")

        # Mark invalid custom option keys with red border and tooltip
        for row_widget in self.custom_options_list:
            row_content_box = row_widget.get_child()
            if row_content_box and isinstance(row_content_box, Gtk.Box):
                key_entry = row_content_box.get_first_child()
                if key_entry and isinstance(key_entry, Gtk.Entry):
                    key = key_entry.get_text().strip()
                    key_entry.remove_css_class("entry-error")
                    if not key:
                        key_entry.add_css_class("entry-error")
                        key_entry.set_tooltip_text(_("Custom option key cannot be empty."))

        # Apply inline error texts
        if 'patterns' in errors:
            self.patterns_error_label.set_text(errors['patterns'])
            self.patterns_error_label.set_visible(True)
            self.patterns_entry.add_css_class("entry-error")
        else:
            self.patterns_entry.remove_css_class("entry-error")
        if 'port' in errors:
            self.port_error_label.set_text(errors['port'])
            self.port_error_label.set_visible(True)
            self.port_entry.add_css_class("entry-error")
        else:
            self.port_entry.remove_css_class("entry-error")

        return errors

    def _clear_field_errors(self):
        if hasattr(self, 'patterns_error_label'):
            self.patterns_error_label.set_visible(False)
        if hasattr(self, 'port_error_label'):
            self.port_error_label.set_visible(False)
        if hasattr(self, 'patterns_entry'):
            self.patterns_entry.remove_css_class("entry-error")
        if hasattr(self, 'port_entry'):
            self.port_entry.remove_css_class("entry-error")
        # Clear custom options error styling
        for row_widget in self.custom_options_list:
            row_content_box = row_widget.get_child()
            if row_content_box and isinstance(row_content_box, Gtk.Box):
                key_entry = row_content_box.get_first_child()
                if key_entry and isinstance(key_entry, Gtk.Entry):
                    key_entry.remove_css_class("entry-error")

    def _validate_and_update_host(self):
        field_errors = self._collect_field_errors()
        if field_errors:
            self.emit("editor-validity-changed", False)
            return
        else:
            self.emit("editor-validity-changed", True)

        self._update_host_from_fields()
        self.emit("host-changed", self.current_host)
        GLib.idle_add(lambda: (self._update_raw_text_from_host(), False)[1])

    def _on_revert_clicked(self, button):
        """Reverts the current host's changes to its last loaded state by reloading the configuration."""
        if not self.current_host:
            return

        if not hasattr(self, 'original_host_state') or not self.original_host_state:
            return
        self.is_loading = True
        self.current_host.patterns = copy.deepcopy(self.original_host_state.patterns)
        self.current_host.options = copy.deepcopy(self.original_host_state.options)
        self.current_host.raw_lines = copy.deepcopy(self.original_host_state.raw_lines)

        self._sync_fields_from_host()

        buffer = self.raw_text_view.get_buffer()
        if hasattr(self, "_raw_changed_handler_id"):
            buffer.handler_block(self._raw_changed_handler_id)
        self._programmatic_raw_update = True
        buffer.set_text("\n".join(self.current_host.raw_lines))
        if hasattr(self, "_raw_changed_handler_id"):
            buffer.handler_unblock(self._raw_changed_handler_id)
        self._programmatic_raw_update = False
        self.original_raw_content = "\n".join(self.current_host.raw_lines)
        self.is_loading = False

        if self.buffer is not None:
            self.buffer.remove_all_tags(self.buffer.get_start_iter(), self.buffer.get_end_iter())
        self.emit("host-changed", self.current_host)
        self.revert_button.set_sensitive(False)
        self.app._show_toast(_(f"Reverted changes for {self.current_host.patterns[0]}"))

    def _on_test_connection(self, button):
        if not self.current_host:
            return
        
        dialog = Gtk.Dialog(
            title=_("Test Connection"),
            transient_for=self.get_root(),
            modal=True
        )
        
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.set_resizable(True)
        dialog.set_default_size(900, 600)
        
        content_area = dialog.get_content_area()
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        
        status_label = Gtk.Label(label=_("Running SSH command..."))
        status_label.set_margin_bottom(12)
        content_area.append(status_label)

        output_text_view = Gtk.TextView()
        output_text_view.set_editable(False)
        output_text_view.set_monospace(True)
        output_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        output_text_view.set_vexpand(True)
        output_text_buffer = output_text_view.get_buffer()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(output_text_view)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        content_area.append(scrolled_window)
        
        # Construct the SSH command, using -G for configuration parsing only
        hostname = self.hostname_entry.get_text().strip()
        if not hostname and self.current_host.patterns:
            hostname = self.current_host.patterns[0] # Fallback to pattern if hostname is empty

        if not hostname:
            status_label.set_text(_("Error: No hostname or pattern available to test."))
            dialog.present()
            return

        # Use host SSH when running inside Flatpak
        ssh_invocation = ["ssh"]
        try:
            if os.environ.get("FLATPAK_ID"):
                ssh_invocation = ["flatpak-spawn", "--host", "ssh"]
        except Exception:
            pass

        command = [*ssh_invocation,
                   "-q",
                   "-T",
                   "-o", "BatchMode=yes",
                   "-o", "ConnectTimeout=8",
                   "-o", "StrictHostKeyChecking=accept-new",
                   "-o", "PasswordAuthentication=no",
                   "-o", "KbdInteractiveAuthentication=no",
                   "-o", "NumberOfPasswordPrompts=0",
                   "-o", "ControlMaster=no",
                   "-o", "ControlPath=none",
                   "-o", "ControlPersist=no"]

        # Include common fields from the editor
        user_val = self.user_entry.get_text().strip()
        port_val = self.port_entry.get_text().strip()
        ident_val = self.identity_entry.get_text().strip()
        proxy_jump_val = self.proxy_jump_entry.get_text().strip()

        if user_val:
            command += ["-l", user_val]
        if port_val:
            command += ["-p", port_val]
        if ident_val:
            command += ["-i", ident_val]
        if proxy_jump_val:
            command += ["-J", proxy_jump_val]

        command += [hostname, "exit"]

        # Execute the command on a background thread to avoid blocking the UI
        def run_test():
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=20
                )
                rc = result.returncode
                stdout_text = (result.stdout or "").strip()
                stderr_text = (result.stderr or "").strip()

                def update_ui():
                    summary = _("Connection OK") if rc == 0 else _(f"Connection failed (exit {rc})")
                    status_label.set_text(summary)
                    output = f"Command: {' '.join(command)}\n\n"
                    if stdout_text:
                        output += _(f"STDOUT:\n{stdout_text}\n\n")
                    if stderr_text:
                        output += _(f"STDERR:\n{stderr_text}\n\n")
                    output += summary
                    output_text_buffer.set_text(output)
                    return False

                GLib.idle_add(update_ui)

            except subprocess.TimeoutExpired:
                def update_timeout():
                    status_label.set_text(_("Connection timed out"))
                    output_text_buffer.set_text(_(f"Command: {' '.join(command)}\n\nTimed out after 20s"))
                    return False
                GLib.idle_add(update_timeout)
            except Exception as e:
                def update_error():
                    status_label.set_text(_(f"Error: {e}"))
                    output_text_buffer.set_text(str(e))
                    return False
                GLib.idle_add(update_error)

        threading.Thread(target=run_test, daemon=True).start()

        dialog.present()

    def _sync_fields_from_host(self):
        if not self.current_host:
            return
        self.is_loading = True
        self.patterns_entry.set_text(" ".join(self.current_host.patterns))
        self.hostname_entry.set_text(self.current_host.get_option('HostName') or "")
        self.user_entry.set_text(self.current_host.get_option('User') or "")
        self.port_entry.set_text(self.current_host.get_option('Port') or "")
        self.identity_entry.set_text(self.current_host.get_option('IdentityFile') or "")
        self.forward_agent_switch.set_active((self.current_host.get_option('ForwardAgent') or "").lower() == 'yes')
        self.proxy_jump_entry.set_text(self.current_host.get_option('ProxyJump') or "")
        self.proxy_cmd_entry.set_text(self.current_host.get_option('ProxyCommand') or "")
        self.local_forward_entry.set_text(self.current_host.get_option('LocalForward') or "")
        self.remote_forward_entry.set_text(self.current_host.get_option('RemoteForward') or "")
        self._load_custom_options(self.current_host)
        self.is_loading = False
