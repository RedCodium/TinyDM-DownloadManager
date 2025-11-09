import customtkinter as ctk
import tkinter as tk
from download_manager import DownloadManager
import threading
import time
import os

class DownloadApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("TinyDM - Download Manager")
        self.geometry("800x600")
        
        # Initialize download manager
        self.download_manager = DownloadManager()
        self.downloads_ui = {}
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Create URL entry frame
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Enter download URL...", width=600)
        self.url_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        self.download_button = ctk.CTkButton(self.url_frame, text="Download", command=self.add_download)
        self.download_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create downloads frame with scrollbar
        self.downloads_frame_outer = ctk.CTkFrame(self)
        self.downloads_frame_outer.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.downloads_frame_outer.grid_columnconfigure(0, weight=1)
        self.downloads_frame_outer.grid_rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self.downloads_frame_outer, bg=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"]))
        self.scrollbar = ctk.CTkScrollbar(self.downloads_frame_outer, command=self.canvas.yview)
        self.downloads_frame = ctk.CTkFrame(self.canvas)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollbar and canvas
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Create window in canvas
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.downloads_frame, anchor="nw")
        
        # Configure canvas and frame
        self.downloads_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Load existing downloads
        self.load_existing_downloads()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self.update_progress, daemon=True)
        self.update_thread.start()

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def add_download(self):
        url = self.url_entry.get().strip()
        if url:
            download_id = self.download_manager.add_download(url)
            self.create_download_frame(download_id)
            self.download_manager.start_download(download_id)
            self.url_entry.delete(0, tk.END)

    def create_download_frame(self, download_id):
        info = self.download_manager.get_download_info(download_id)
        if not info:
            return
        
        frame = ctk.CTkFrame(self.downloads_frame)
        frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
        
        filename_label = ctk.CTkLabel(frame, text=info['filename'], anchor="w")
        filename_label.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        
        progress_bar = ctk.CTkProgressBar(frame, width=400)
        progress_bar.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        progress_bar.set(0)
        
        status_label = ctk.CTkLabel(frame, text="Pending...")
        status_label.grid(row=1, column=1, padx=5, pady=2)
        
        button_frame = ctk.CTkFrame(frame)
        button_frame.grid(row=1, column=2, padx=5, pady=2)
        
        pause_button = ctk.CTkButton(button_frame, text="Pause", width=70,
                                   command=lambda: self.toggle_pause(download_id))
        pause_button.pack(side=tk.LEFT, padx=2)
        
        self.downloads_ui[download_id] = {
            'frame': frame,
            'progress': progress_bar,
            'status': status_label,
            'pause_button': pause_button
        }
        
        frame.grid_columnconfigure(0, weight=1)
        self.on_frame_configure()

    def toggle_pause(self, download_id):
        info = self.download_manager.get_download_info(download_id)
        if info['status'] == 'downloading':
            self.download_manager.pause_download(download_id)
            self.downloads_ui[download_id]['pause_button'].configure(text="Resume")
        elif info['status'] == 'paused':
            self.download_manager.start_download(download_id)
            self.downloads_ui[download_id]['pause_button'].configure(text="Pause")

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def update_download_ui(self, download_id):
        if download_id not in self.downloads_ui:
            return
        
        info = self.download_manager.get_download_info(download_id)
        ui = self.downloads_ui[download_id]
        
        progress = 0 if info['total_size'] == 0 else info['downloaded'] / info['total_size']
        ui['progress'].set(progress)
        
        status_text = f"{self.format_size(info['downloaded'])}"
        if info['total_size'] > 0:
            status_text += f" / {self.format_size(info['total_size'])}"
        status_text += f" ({int(progress * 100)}%)"
        ui['status'].configure(text=status_text)
        
        if info['status'] == 'completed':
            ui['pause_button'].configure(state="disabled", text="Completed")
        elif info['status'] == 'error':
            ui['pause_button'].configure(state="disabled", text="Error")

    def load_existing_downloads(self):
        for download_id in self.download_manager.downloads:
            self.create_download_frame(download_id)
            info = self.download_manager.get_download_info(download_id)
            if info['status'] == 'downloading':
                self.download_manager.start_download(download_id)

    def update_progress(self):
        while True:
            for download_id in list(self.downloads_ui.keys()):
                self.update_download_ui(download_id)
            time.sleep(0.1)

if __name__ == "__main__":
    app = DownloadApp()
    app.mainloop()