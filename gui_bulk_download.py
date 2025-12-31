#!/usr/bin/env python3
"""
E-Paket Bulk Download GUI Application - HORIZONTAL CHECKBOXES
============================================================

A user-friendly tkinter interface for bulk downloading documents from the E-Paket system.
Document type checkboxes are displayed horizontally for better UX.
Supports English and Indonesian languages with flag selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import sys
from datetime import datetime

# Import our custom modules
from session_validator import SessionValidator
from enhanced_downloader import EnhancedDownloader

class EPGUIApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("E-Paket Bulk Download Tool")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Initialize components
        self.validator = SessionValidator()
        self.downloader = None
        self.is_downloading = False
        
        # Language settings (English default)
        self.current_language = "en"
        self.translations = {
            "en": {
                "title": "E-Paket Bulk Download Tool",
                "session_management": "1. Session Management",
                "session_cookie": "Session Cookie:",
                "status": "Status:",
                "not_validated": "Not validated",
                "validate_session": "Validate Session",
                "validating": "Validating...",
                "document_selection": "2. Document Type Selection",
                "select_documents": "Select document types to download:",
                "download_controls": "3. Download Controls",
                "start_download": "Start Bulk Download",
                "stop_download": "Stop Download",
                "clear_status": "Clear Status",
                "progress_tracking": "4. Progress Tracking",
                "progress": "Progress:",
                "ready": "Ready",
                "status_log": "5. Status Log",
                "session_help_title": "How to Get Session Cookie",
                "session_help_text": """How to Get Session Cookie:

1. Open your browser and log into the E-Paket system
2. Press F12 to open Developer Tools
3. Go to the Network tab
4. Refresh the page
5. Click on any request to the server
6. Find the 'Cookie' header and copy the ci_session value
7. Paste it in the Session Cookie field""",
                "warning": "Warning",
                "enter_session": "Please enter a session cookie",
                "select_one_doc": "Please select at least one document type",
                "confirm": "Confirm",
                "confirm_download": "Start downloading {doc_list} documents?\n\nThis may take several minutes.",
                "starting_download": "Starting bulk download...",
                "document_types_label": "Document types: {doc_list}",
                "success": "Success",
                "download_completed": "Download completed!",
                "downloaded": "Downloaded",
                "skipped": "Skipped",
                "errors": "Errors",
                "files": "files",
                "error": "Error",
                "download_failed": "Download failed: {error}",
                "download_error": "Download error: {error}",
                "stopping_download": "Stopping download...",
                "download_completed_msg": "Download completed successfully!",
                "akte_kematian": "Death Certificate",
                "akte_kelahiran": "Birth Certificate",
                "kartu_keluarga": "Family Card",
                "workers": "Concurrent Workers:",
                "workers_hint": "(1-10, higher = faster but more server load)"
            },
            "id": {
                "title": "E-Paket Unduh Massal",
                "session_management": "1. Manajemen Sesi",
                "session_cookie": "Cookie Sesi:",
                "status": "Status:",
                "not_validated": "Belum divalidasi",
                "validate_session": "Validasi Sesi",
                "validating": "Memvalidasi...",
                "document_selection": "2. Pilih Jenis Dokumen",
                "select_documents": "Pilih jenis dokumen untuk diunduh:",
                "download_controls": "3. Kontrol Unduhan",
                "start_download": "Mulai Unduh Massal",
                "stop_download": "Hentikan Unduhan",
                "clear_status": "Bersihkan Status",
                "progress_tracking": "4. Pelacakan Progres",
                "progress": "Progres:",
                "ready": "Siap",
                "status_log": "5. Log Status",
                "session_help_title": "Cara Mendapatkan Cookie Sesi",
                "session_help_text": """Cara Mendapatkan Cookie Sesi:

1. Buka browser dan masuk ke sistem E-Paket
2. Tekan F12 untuk membuka Developer Tools
3. Pergi ke tab Network
4. Refresh halaman
5. Klik pada permintaan apapun ke server
6. Temukan header 'Cookie' dan salin nilai ci_session
7. Tempelkan di kolom Cookie Sesi""",
                "warning": "Peringatan",
                "enter_session": "Silakan masukkan cookie sesi",
                "select_one_doc": "Silakan pilih setidaknya satu jenis dokumen",
                "confirm": "Konfirmasi",
                "confirm_download": "Mulai mengunduh dokumen {doc_list}?\n\nIni mungkin membutuhkan beberapa menit.",
                "starting_download": "Memulai unduhan massal...",
                "document_types_label": "Jenis dokumen: {doc_list}",
                "success": "Berhasil",
                "download_completed": "Unduhan selesai!",
                "downloaded": "Diunduh",
                "skipped": "Dilewati",
                "errors": "Kesalahan",
                "files": "file",
                "error": "Kesalahan",
                "download_failed": "Unduhan gagal: {error}",
                "download_error": "Kesalahan unduhan: {error}",
                "stopping_download": "Menghentikan unduhan...",
                "download_completed_msg": "Unduhan selesai dengan sukses!",
                "akte_kematian": "Akte Kematian",
                "akte_kelahiran": "Akte Kelahiran",
                "kartu_keluarga": "Kartu Keluarga",
                "workers": "Pekerja Simultan:",
                "workers_hint": "(1-10, lebih tinggi = lebih cepat tapi beban server lebih besar)"
            }
        }
        
        # Available document types - FIXED: Use spaces instead of underscores for API
        self.document_types = {
            "akte_kematian": "AKTE KEMATIAN",
            "akte_kelahiran": "AKTE KELAHIRAN", 
            "kartu_keluarga": "KARTU KELUARGA"
        }
        
        # GUI variables
        self.session_cookie_var = tk.StringVar()
        self.session_valid_var = tk.StringVar(value=self.get_text("not_validated"))
        self.worker_count_var = tk.IntVar(value=5)  # Default 5 concurrent workers
        self.selected_documents = []
        
        self.setup_gui()
    
    def get_text(self, key):
        """Get translated text for current language."""
        return self.translations[self.current_language].get(key, key)
    
    def get_document_display_name(self, doc_key):
        """Get translated document name."""
        return self.get_text(doc_key)
        
    def setup_gui(self):
        """Setup the main GUI layout."""
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        
        # Store main_frame reference for language updates
        self.main_frame = main_frame
        
        # Language selection (top left)
        self.create_language_section(main_frame, 0)
        
        # Title
        self.title_label = ttk.Label(main_frame, text=self.get_text("title"), 
                               font=("Arial", 16, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Session Management Section
        self.create_session_section(main_frame, 1)
        
        # Document Selection Section
        self.create_document_section(main_frame, 4)
        
        # Download Controls Section
        self.create_download_section(main_frame, 7)
        
        # Progress Section
        self.create_progress_section(main_frame, 10)
        
        # Status Section
        self.create_status_section(main_frame, 13)
        
    def create_language_section(self, parent, start_row):
        """Create language selection section with flag buttons."""
        lang_frame = ttk.Frame(parent)
        lang_frame.grid(row=start_row, column=0, sticky=tk.W, pady=(0, 5))
        
        # English flag button (🇺🇸 or EN)
        self.en_btn = tk.Button(lang_frame, text="🇺🇸 EN", font=("Arial", 9), 
                               command=lambda: self.switch_language("en"),
                               relief=tk.SUNKEN if self.current_language == "en" else tk.RAISED,
                               width=6)
        self.en_btn.pack(side=tk.LEFT, padx=2)
        
        # Indonesian flag button (🇮🇩 or ID)
        self.id_btn = tk.Button(lang_frame, text="🇮🇩 ID", font=("Arial", 9),
                               command=lambda: self.switch_language("id"),
                               relief=tk.SUNKEN if self.current_language == "id" else tk.RAISED,
                               width=6)
        self.id_btn.pack(side=tk.LEFT, padx=2)
    
    def switch_language(self, lang):
        """Switch the application language and refresh UI."""
        if self.current_language == lang:
            return
            
        self.current_language = lang
        
        # Update button appearance
        if lang == "en":
            self.en_btn.config(relief=tk.SUNKEN)
            self.id_btn.config(relief=tk.RAISED)
        else:
            self.en_btn.config(relief=tk.RAISED)
            self.id_btn.config(relief=tk.SUNKEN)
        
        # Refresh all UI text
        self.refresh_ui_text()
    
    def refresh_ui_text(self):
        """Refresh all UI elements with current language translations."""
        # Update title
        self.root.title(self.get_text("title"))
        self.title_label.config(text=self.get_text("title"))
        
        # Update section labels
        self.session_section_label.config(text=self.get_text("session_management"))
        self.session_cookie_label.config(text=self.get_text("session_cookie"))
        self.session_status_label.config(text=self.get_text("status"))
        self.validate_btn.config(text=self.get_text("validate_session"))
        
        self.doc_section_label.config(text=self.get_text("document_selection"))
        self.doc_instructions_label.config(text=self.get_text("select_documents"))
        
        # Update document checkboxes
        for doc_key, checkbox in self.checkbox_widgets.items():
            checkbox.config(text=self.get_document_display_name(doc_key))
        
        self.download_section_label.config(text=self.get_text("download_controls"))
        self.start_btn.config(text=self.get_text("start_download"))
        self.stop_btn.config(text=self.get_text("stop_download"))
        self.clear_btn.config(text=self.get_text("clear_status"))
        
        # Update worker labels
        self.workers_label.config(text=self.get_text("workers"))
        self.workers_hint_label.config(text=self.get_text("workers_hint"))
        
        self.progress_section_label.config(text=self.get_text("progress_tracking"))
        self.progress_text_label.config(text=self.get_text("progress"))
        self.progress_label.config(text=self.get_text("ready"))
        
        self.status_section_label.config(text=self.get_text("status_log"))
        
        # Update session valid status if not validated
        if "✓" not in self.session_valid_var.get():
            self.session_valid_var.set(self.get_text("not_validated"))
    
    def show_session_help(self):
        """Show session cookie help dialog."""
        messagebox.showinfo(
            self.get_text("session_help_title"),
            self.get_text("session_help_text")
        )
    
    def create_session_section(self, parent, start_row):
        """Create session management section."""
        # Section title
        self.session_section_label = ttk.Label(parent, text=self.get_text("session_management"), 
                                 font=("Arial", 12, "bold"))
        self.session_section_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        
        # Session cookie label frame (with help button)
        cookie_label_frame = ttk.Frame(parent)
        cookie_label_frame.grid(row=start_row+1, column=0, sticky=tk.W, pady=2)
        
        # Help button (question mark icon)
        help_btn = tk.Button(cookie_label_frame, text="❓", font=("Arial", 8), 
                            command=self.show_session_help, width=2, height=1,
                            relief=tk.FLAT, cursor="hand2")
        help_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.session_cookie_label = ttk.Label(cookie_label_frame, text=self.get_text("session_cookie"))
        self.session_cookie_label.pack(side=tk.LEFT)
        
        session_frame = ttk.Frame(parent)
        session_frame.grid(row=start_row+1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        session_frame.columnconfigure(0, weight=1)
        
        self.session_entry = ttk.Entry(session_frame, textvariable=self.session_cookie_var, 
                                      font=("Courier", 10))
        self.session_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.validate_btn = ttk.Button(session_frame, text=self.get_text("validate_session"), 
                                      command=self.validate_session)
        self.validate_btn.grid(row=0, column=1)
        
        # Session status
        self.session_status_label = ttk.Label(parent, text=self.get_text("status"))
        self.session_status_label.grid(row=start_row+2, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(parent, textvariable=self.session_valid_var, 
                                     foreground="red")
        self.status_label.grid(row=start_row+2, column=1, columnspan=2, sticky=tk.W, pady=2)
        
    def create_document_section(self, parent, start_row):
        """Create document type selection section with HORIZONTAL checkboxes."""
        # Section title
        self.doc_section_label = ttk.Label(parent, text=self.get_text("document_selection"), 
                             font=("Arial", 12, "bold"))
        self.doc_section_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        
        # Instructions
        self.doc_instructions_label = ttk.Label(parent, text=self.get_text("select_documents"), 
                 font=("Arial", 10))
        self.doc_instructions_label.grid(row=start_row+1, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Create horizontal checkbox frame
        checkbox_frame = ttk.Frame(parent)
        checkbox_frame.grid(row=start_row+2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Configure frame columns for equal distribution
        num_types = len(self.document_types)
        for i in range(num_types):
            checkbox_frame.columnconfigure(i, weight=1)
        
        # Document checkboxes - HORIZONTAL LAYOUT
        self.document_vars = {}
        self.checkbox_widgets = {}
        for i, (doc_key, actual_name) in enumerate(self.document_types.items()):
            var = tk.BooleanVar()
            self.document_vars[actual_name] = var
            
            checkbox = ttk.Checkbutton(checkbox_frame, text=self.get_document_display_name(doc_key), 
                                      variable=var, command=self.on_document_selection_change)
            checkbox.grid(row=0, column=i, sticky=tk.W, padx=15, pady=5)
            self.checkbox_widgets[doc_key] = checkbox
            
    def create_download_section(self, parent, start_row):
        """Create download controls section."""
        # Section title
        self.download_section_label = ttk.Label(parent, text=self.get_text("download_controls"), 
                                  font=("Arial", 12, "bold"))
        self.download_section_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        
        # Buttons frame
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=start_row+1, column=0, columnspan=3, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text=self.get_text("start_download"), 
                                   command=self.start_download, state="disabled")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text=self.get_text("stop_download"), 
                                  command=self.stop_download, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(button_frame, text=self.get_text("clear_status"), 
                                   command=self.clear_status)
        self.clear_btn.pack(side=tk.LEFT)
        
        # Worker count configuration
        worker_frame = ttk.Frame(parent)
        worker_frame.grid(row=start_row+2, column=0, columnspan=3, pady=(5, 10))
        
        self.workers_label = ttk.Label(worker_frame, text=self.get_text("workers"))
        self.workers_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.worker_spinbox = ttk.Spinbox(worker_frame, from_=1, to=10, width=5,
                                         textvariable=self.worker_count_var)
        self.worker_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        self.workers_hint_label = ttk.Label(worker_frame, text=self.get_text("workers_hint"),
                                           font=("Arial", 8), foreground="gray")
        self.workers_hint_label.pack(side=tk.LEFT)
        
    def create_progress_section(self, parent, start_row):
        """Create progress tracking section."""
        # Section title
        self.progress_section_label = ttk.Label(parent, text=self.get_text("progress_tracking"), 
                                  font=("Arial", 12, "bold"))
        self.progress_section_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        
        # Progress bar
        self.progress_text_label = ttk.Label(parent, text=self.get_text("progress"))
        self.progress_text_label.grid(row=start_row+1, column=0, sticky=tk.W, pady=2)
        
        self.progress_bar = ttk.Progressbar(parent, mode='determinate', length=400)
        self.progress_bar.grid(row=start_row+1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # Progress details
        self.progress_label = ttk.Label(parent, text=self.get_text("ready"), foreground="blue")
        self.progress_label.grid(row=start_row+2, column=0, columnspan=3, sticky=tk.W, pady=2)
        
    def create_status_section(self, parent, start_row):
        """Create status display section."""
        # Section title
        self.status_section_label = ttk.Label(parent, text=self.get_text("status_log"), 
                                font=("Arial", 12, "bold"))
        self.status_section_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        
        # Status text area
        self.status_text = scrolledtext.ScrolledText(parent, height=12, width=80, 
                                                    font=("Courier", 9))
        self.status_text.grid(row=start_row+1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights for resizing
        parent.rowconfigure(start_row+1, weight=1)
        
    def on_document_selection_change(self):
        """Handle document selection changes."""
        self.selected_documents = [doc_type for doc_type, var in self.document_vars.items() if var.get()]
        self.update_start_button_state()
        
    def update_start_button_state(self):
        """Update the start button state based on validation and selection."""
        session_valid = "✓" in self.session_valid_var.get()
        has_documents = len(self.selected_documents) > 0
        
        if session_valid and has_documents and not self.is_downloading:
            self.start_btn.config(state="normal")
        else:
            self.start_btn.config(state="disabled")
            
    def validate_session(self):
        """Validate the session cookie."""
        session_cookie = self.session_cookie_var.get().strip()
        
        if not session_cookie:
            messagebox.showwarning(self.get_text("warning"), self.get_text("enter_session"))
            return
            
        # Disable validate button during validation
        self.validate_btn.config(state="disabled", text=self.get_text("validating"))
        self.root.config(cursor="wait")
        
        def validate_thread():
            try:
                is_valid, message = self.validator.validate_session(session_cookie)
                
                # Update GUI in main thread
                self.root.after(0, lambda: self.update_session_validation(is_valid, message))
                
            except Exception as e:
                self.root.after(0, lambda: self.update_session_validation(False, f"Error: {str(e)}"))
        
        threading.Thread(target=validate_thread, daemon=True).start()
        
    def update_session_validation(self, is_valid, message):
        """Update session validation result in GUI."""
        self.validate_btn.config(state="normal", text=self.get_text("validate_session"))
        self.root.config(cursor="")
        
        self.session_valid_var.set(message)
        
        if is_valid:
            self.status_label.config(foreground="green")
        else:
            self.status_label.config(foreground="red")
            
        self.update_start_button_state()
        
    def start_download(self):
        """Start the bulk download process."""
        session_cookie = self.session_cookie_var.get().strip()
        
        if not session_cookie:
            messagebox.showwarning(self.get_text("warning"), self.get_text("enter_session"))
            return
            
        if not self.selected_documents:
            messagebox.showwarning(self.get_text("warning"), self.get_text("select_one_doc"))
            return
            
        # Confirm download
        doc_list = ", ".join([k.replace("_", " ") for k in self.selected_documents])
        confirm_msg = self.get_text("confirm_download").format(doc_list=doc_list)
        if not messagebox.askyesno(self.get_text("confirm"), confirm_msg):
            return
            
        self.is_downloading = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.validate_btn.config(state="disabled")
        
        # Disable document selection during download
        for var in self.document_vars.values():
            var.set(False)  # This will be re-enabled after download
            
        self.log_status(self.get_text("starting_download"), "info")
        self.log_status(self.get_text("document_types_label").format(doc_list=doc_list), "info")
        
        # Start download in separate thread
        worker_count = self.worker_count_var.get()
        self.downloader = EnhancedDownloader(max_workers=worker_count)
        self.downloader.set_callbacks(self.update_progress, self.log_status)
        
        def download_thread():
            try:
                result = self.downloader.bulk_download(self.selected_documents, session_cookie)
                
                # Update GUI in main thread
                self.root.after(0, lambda: self.download_completed(result))
                
            except Exception as e:
                self.root.after(0, lambda: self.download_error(str(e)))
        
        threading.Thread(target=download_thread, daemon=True).start()
        
    def stop_download(self):
        """Stop the download process."""
        if self.downloader:
            self.downloader.stop_download()
            self.log_status(self.get_text("stopping_download"), "warning")
            
    def download_completed(self, result):
        """Handle download completion."""
        self.is_downloading = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.validate_btn.config(state="normal")
        
        if result["success"]:
            self.log_status(self.get_text("download_completed_msg"), "success")
            self.log_status(f"{self.get_text('downloaded')}: {result['downloaded']} {self.get_text('files')}", "info")
            self.log_status(f"{self.get_text('skipped')}: {result['skipped']} {self.get_text('files')}", "info")
            self.log_status(f"{self.get_text('errors')}: {result['errors']} {self.get_text('files')}", "info")
            
            messagebox.showinfo(self.get_text("success"), 
                              f"{self.get_text('download_completed')}\n\n"
                              f"{self.get_text('downloaded')}: {result['downloaded']} {self.get_text('files')}\n"
                              f"{self.get_text('skipped')}: {result['skipped']} {self.get_text('files')}\n"
                              f"{self.get_text('errors')}: {result['errors']} {self.get_text('files')}")
        else:
            error_msg = result.get("error", "Unknown error")
            self.log_status(self.get_text("download_failed").format(error=error_msg), "error")
            messagebox.showerror(self.get_text("error"), self.get_text("download_failed").format(error=error_msg))
            
        self.update_start_button_state()
        
    def download_error(self, error_msg):
        """Handle download error."""
        self.is_downloading = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.validate_btn.config(state="normal")
        
        self.log_status(self.get_text("download_error").format(error=error_msg), "error")
        messagebox.showerror(self.get_text("error"), self.get_text("download_error").format(error=error_msg))
        
        self.update_start_button_state()
        
    def update_progress(self, current, total, percentage, message):
        """Update progress bar and label."""
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = current
        
        progress_text = f"{current}/{total} ({percentage:.1f}%) - {message}"
        self.progress_label.config(text=progress_text)
        
    def log_status(self, message, level="info"):
        """Add message to status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding for different levels
        colors = {
            "info": "black",
            "success": "green", 
            "warning": "orange",
            "error": "red"
        }
        
        color = colors.get(level, "black")
        
        # Add to text widget
        self.status_text.config(state=tk.NORMAL)
        
        # Add timestamp and level
        self.status_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.status_text.insert(tk.END, f"[{level.upper()}] ", level)
        
        # Add message
        self.status_text.insert(tk.END, f"{message}\n", "message")
        
        # Configure tags for colors
        self.status_text.tag_config("timestamp", foreground="gray")
        self.status_text.tag_config(level, foreground=color)
        self.status_text.tag_config("message", foreground=color)
        
        # Auto-scroll to bottom
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
    def clear_status(self):
        """Clear the status log."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # Reset progress
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Ready")

def main():
    """Main function to run the GUI application."""
    root = tk.Tk()
    app = EPGUIApplication(root)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
