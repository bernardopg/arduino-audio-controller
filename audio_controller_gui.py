#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
import serial
import serial.tools.list_ports
import pulsectl
import threading
import time

class AudioControllerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.bitter.audiocontroller')
        self.pulse = pulsectl.Pulse('audio-controller')
        self.ser = None
        self.running = False
        self.app1_name = "chrome"
        self.app2_name = "spotify"
        
    def do_activate(self):
        self.window = AudioControllerWindow(self)
        self.window.present()
        
class AudioControllerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="🎛️ Controlador de Áudio")
        self.app = app
        self.set_default_size(400, 600)
        
        # Header Bar
        header = Adw.HeaderBar()
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        header.pack_end(menu_button)
        
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(main_box)
        
        self.set_content(toolbar_view)
        
        # Status card
        self.status_group = Adw.PreferencesGroup()
        self.status_group.set_title("Status da Conexão")
        
        self.status_row = Adw.ActionRow()
        self.status_row.set_title("Arduino")
        self.status_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.status_row.add_suffix(self.status_icon)
        self.status_group.add(self.status_row)
        
        # Volume indicators
        self.volume_group = Adw.PreferencesGroup()
        self.volume_group.set_title("Níveis de Volume")
        self.volume_group.set_margin_top(20)
        
        # Master volume
        self.master_row = Adw.ActionRow()
        self.master_row.set_title("🔊 Volume Master")
        self.master_label = Gtk.Label(label="---%")
        self.master_label.set_width_chars(5)
        self.master_row.add_suffix(self.master_label)
        self.master_progress = Gtk.LevelBar()
        self.master_progress.set_min_value(0)
        self.master_progress.set_max_value(100)
        self.master_progress.set_hexpand(True)
        self.master_progress.set_margin_top(8)
        master_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        master_box.append(self.master_row)
        master_box.append(self.master_progress)
        self.volume_group.add(master_box)
        
        # App 1 volume (Chrome)
        self.app1_row = Adw.ActionRow()
        self.app1_row.set_title("🌐 Google Chrome")
        self.app1_label = Gtk.Label(label="---%")
        self.app1_label.set_width_chars(5)
        self.app1_row.add_suffix(self.app1_label)
        self.app1_progress = Gtk.LevelBar()
        self.app1_progress.set_min_value(0)
        self.app1_progress.set_max_value(100)
        self.app1_progress.set_hexpand(True)
        self.app1_progress.set_margin_top(8)
        app1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        app1_box.append(self.app1_row)
        app1_box.append(self.app1_progress)
        self.volume_group.add(app1_box)
        
        # App 2 volume (Spotify)
        self.app2_row = Adw.ActionRow()
        self.app2_row.set_title("🎵 Spotify")
        self.app2_label = Gtk.Label(label="---%")
        self.app2_label.set_width_chars(5)
        self.app2_row.add_suffix(self.app2_label)
        self.app2_progress = Gtk.LevelBar()
        self.app2_progress.set_min_value(0)
        self.app2_progress.set_max_value(100)
        self.app2_progress.set_hexpand(True)
        self.app2_progress.set_margin_top(8)
        app2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        app2_box.append(self.app2_row)
        app2_box.append(self.app2_progress)
        self.volume_group.add(app2_box)
        
        # Control buttons
        self.control_group = Adw.PreferencesGroup()
        self.control_group.set_margin_top(20)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)
        button_box.set_margin_bottom(12)
        
        self.start_button = Gtk.Button(label="▶ Iniciar")
        self.start_button.add_css_class("suggested-action")
        self.start_button.set_size_request(150, 40)
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.append(self.start_button)
        
        self.stop_button = Gtk.Button(label="⏹ Parar")
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.set_size_request(150, 40)
        self.stop_button.set_sensitive(False)
        self.stop_button.connect("clicked", self.on_stop_clicked)
        button_box.append(self.stop_button)
        
        self.control_group.add(button_box)
        
        # Add all groups to main box
        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.append(self.status_group)
        content_box.append(self.volume_group)
        content_box.append(self.control_group)
        clamp.set_child(content_box)
        main_box.append(clamp)
        
        # Auto-start
        GLib.timeout_add(1000, self.auto_start)
        
    def auto_start(self):
        self.on_start_clicked(None)
        return False
        
    def on_start_clicked(self, button):
        if self.app.running:
            return
            
        # Find Arduino
        ports = serial.tools.list_ports.comports()
        arduino_port = None
        for port in ports:
            if 'USB' in port.device or 'ACM' in port.device:
                arduino_port = port.device
                break
        
        if not arduino_port:
            self.update_status("❌ Desconectado", False)
            return
            
        try:
            self.app.ser = serial.Serial(arduino_port, 9600, timeout=1)
            time.sleep(2)
            self.app.running = True
            self.update_status("✅ Conectado", True)
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(True)
            
            # Start reading thread
            thread = threading.Thread(target=self.read_arduino, daemon=True)
            thread.start()
        except Exception as e:
            self.update_status(f"❌ Erro: {e}", False)
            
    def on_stop_clicked(self, button):
        self.app.running = False
        if self.app.ser:
            self.app.ser.close()
        self.update_status("⏹ Parado", False)
        self.start_button.set_sensitive(True)
        self.stop_button.set_sensitive(False)
        
    def read_arduino(self):
        while self.app.running:
            try:
                if self.app.ser.in_waiting > 0:
                    line = self.app.ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if ':' not in line:
                        continue
                    
                    pot, val = line.split(':', 1)
                    value = int(val)
                    volume = max(0.0, min(1.0, value / 1023.0))
                    percent = int(volume * 100)
                    
                    if pot == 'P1':
                        GLib.idle_add(self.update_master, volume, percent)
                    elif pot == 'P2':
                        GLib.idle_add(self.update_app1, volume, percent)
                    elif pot == 'P3':
                        GLib.idle_add(self.update_app2, volume, percent)
                        
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(0.1)
                
    def update_master(self, volume, percent):
        try:
            for sink in self.app.pulse.sink_list():
                self.app.pulse.volume_set_all_chans(sink, volume)
            self.master_label.set_label(f"{percent}%")
            self.master_progress.set_value(percent)
        except:
            pass
        return False
        
    def update_app1(self, volume, percent):
        try:
            for sink_input in self.app.pulse.sink_input_list():
                app = sink_input.proplist.get('application.name', '').lower()
                if self.app.app1_name in app:
                    self.app.pulse.volume_set_all_chans(sink_input, volume)
                    self.app1_label.set_label(f"{percent}%")
                    self.app1_progress.set_value(percent)
                    break
        except:
            pass
        return False
        
    def update_app2(self, volume, percent):
        try:
            for sink_input in self.app.pulse.sink_input_list():
                app = sink_input.proplist.get('application.name', '').lower()
                if self.app.app2_name in app:
                    self.app.pulse.volume_set_all_chans(sink_input, volume)
                    self.app2_label.set_label(f"{percent}%")
                    self.app2_progress.set_value(percent)
                    break
        except:
            pass
        return False
        
    def update_status(self, text, connected):
        self.status_row.set_subtitle(text)
        if connected:
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        else:
            self.status_icon.set_from_icon_name("dialog-error-symbolic")

if __name__ == '__main__':
    app = AudioControllerApp()
    app.run(None)
