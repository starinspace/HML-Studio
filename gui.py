#!/usr/bin/env python3
"""
HeartMuLa Studio - Suno-like GUI for AI Music Generation
A modern interface for HeartLib/HeartMuLa music generation
"""

import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageTk
    import pygame
    import customtkinter as ctk
except ImportError as e:
    print(f"Missing dependencies. Please install requirements.txt")
    print(f"pip install -r requirements.txt")
    print(f"\nImport error: {e}")
    sys.exit(1)

# Configure CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Configure pygame mixer
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Constants
APP_WIDTH = 1400
APP_HEIGHT = 800
SIDEBAR_WIDTH = 420

# Colors (Suno-like dark theme)
COLOR_BG = "#0f172a"
COLOR_BG_LIGHT = "#1e293b"
COLOR_BG_DARK = "#0a0f1c"
COLOR_ACCENT = "#8b5cf6"
COLOR_ACCENT_HOVER = "#7c3aed"
COLOR_TEXT = "#f1f5f9"
COLOR_TEXT_MUTED = "#94a3b8"
COLOR_BORDER = "#334155"
COLOR_ERROR = "#ef4444"


class FileManager:
    """Manages song files and metadata"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / "output"
        self.songs_dir = self.output_dir / "songs"
        self.covers_dir = self.output_dir / "covers"
        self.metadata_dir = self.output_dir / "metadata"

        self.songs_dir.mkdir(parents=True, exist_ok=True)
        self.covers_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_next_unknown_name(self):
        """Get next Unknown_N name for unnamed songs"""
        existing = list(self.songs_dir.glob("Unknown_*.wav"))
        numbers = []
        for f in existing:
            name = f.stem
            if name.startswith("Unknown_"):
                try:
                    num = int(name.split("_")[1])
                    numbers.append(num)
                except:
                    pass
        next_num = 1 if not numbers else max(numbers) + 1
        return f"Unknown_{next_num}"

    def save_metadata(self, title, lyrics, style, genre, song_type, cover_path=None):
        """Save song metadata as JSON"""
        metadata = {
            "title": title,
            "lyrics": lyrics,
            "style": style,
            "genre": genre,
            "type": song_type,
            "cover_path": cover_path,
            "created_at": datetime.now().isoformat()
        }
        metadata_path = self.metadata_dir / f"{title}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return metadata_path

    def load_metadata(self, title):
        """Load song metadata from JSON"""
        metadata_path = self.metadata_dir / f"{title}.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def delete_song_files(self, title):
        """Delete all files associated with a song"""
        files_to_delete = [
            self.songs_dir / f"{title}.wav",
            self.covers_dir / f"{title}.png",
            self.metadata_dir / f"{title}.json"
        ]
        for f in files_to_delete:
            if f.exists():
                try:
                    f.unlink()
                except Exception as e:
                    print(f"Error deleting {f}: {e}")

    def get_all_songs(self):
        """Get list of all generated songs"""
        songs = []
        for wav_file in self.songs_dir.glob("*.wav"):
            title = wav_file.stem
            metadata = self.load_metadata(title)
            songs.append({
                "title": title,
                "wav_path": str(wav_file),
                "cover_path": str(self.covers_dir / f"{title}.png"),
                "metadata": metadata
            })
        songs.sort(key=lambda x: os.path.getmtime(x["wav_path"]), reverse=True)
        return songs


class HeartMuLaStudio(ctk.CTk):
    """Main application window"""

    def __init__(self):
        # Initialize managers first
        self.file_manager = FileManager()

        # State variables
        self.current_cover_path = None
        self.generating = False
        self.playlist = []
        self.current_playlist_index = 0

        # Call parent init
        super().__init__()

        # Load styles database
        self.styles_db = self.load_styles_db()

        # Setup window
        self.setup_window()
        self.setup_layout()
        self.setup_bindings()
        self.load_existing_songs()

        # Start audio update timer
        self.after(100, self.update_audio_ui)

    def load_styles_db(self):
        """Load styles from JSON database"""
        styles_path = Path(__file__).parent / "assets" / "styles_db.json"
        if styles_path.exists():
            with open(styles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"styles": {}, "genres": {}, "types": {}}

    def setup_window(self):
        """Configure main window"""
        self.title("HeartMuLa Studio")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(APP_WIDTH, APP_HEIGHT)
        self.configure(fg_color=COLOR_BG)

        # Center window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - APP_WIDTH) // 2
        y = (screen_height - APP_HEIGHT) // 2
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+{x}+{y}")

    def setup_layout(self):
        """Create main layout"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content()
        self.create_bottom_player()

    def setup_bindings(self):
        """Setup keyboard shortcuts"""
        self.bind("<Control-q>", lambda e: self.destroy())
        self.bind("<F5>", lambda e: self.load_existing_songs())

    # ==================== SIDEBAR SECTIONS ====================

    def create_sidebar(self):
        """Create left sidebar with controls"""
        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLOR_BG_LIGHT
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Title
        ctk.CTkLabel(
            self.sidebar,
            text="HeartMuLa Studio",
            font=("Arial", 24, "bold"),
            text_color=COLOR_ACCENT
        ).pack(pady=(20, 5), padx=20)

        ctk.CTkLabel(
            self.sidebar,
            text="AI Music Generator",
            font=("Arial", 12),
            text_color=COLOR_TEXT_MUTED
        ).pack(pady=(0, 20), padx=20)

        # Scrollable frame
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_fg_color=COLOR_BG_DARK
        )
        self.sidebar_scroll.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        # Sections
        self.create_title_section()
        self.create_cover_section()
        self.create_lyrics_section()
        self.create_style_section()
        self.create_audio_length_section()
        self.create_advanced_section()
        self.create_generate_button()

    def create_title_section(self):
        """Create song title input"""
        frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(
            frame,
            text="Song Title",
            font=("Arial", 14, "bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 5))

        self.title_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Enter song title...",
            height=40,
            border_color=COLOR_BORDER,
            font=("Arial", 12)
        )
        self.title_entry.pack(fill="x")

    def create_cover_section(self):
        """Create cover art upload section"""
        frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15), padx=5)

        # Header
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            header_frame,
            text="Cover Art",
            font=("Arial", 14, "bold"),
            text_color=COLOR_TEXT
        ).pack(side="left")

        # Cover frame
        self.cover_frame = ctk.CTkFrame(
            frame,
            width=150,
            height=150,
            corner_radius=10,
            border_color=COLOR_ACCENT,
            border_width=2
        )
        self.cover_frame.pack(pady=(0, 10))
        self.cover_frame.pack_propagate(False)

        self.cover_label = ctk.CTkLabel(
            self.cover_frame,
            text="+",
            font=("Arial", 48),
            text_color=COLOR_TEXT_MUTED
        )
        self.cover_label.place(relx=0.5, rely=0.5, anchor="center")

        self.cover_instruction = ctk.CTkLabel(
            self.cover_frame,
            text="Click to browse",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED,
            justify="center"
        )
        self.cover_instruction.place(relx=0.5, rely=0.85, anchor="center")

        # Bind events
        for widget in [self.cover_frame, self.cover_label, self.cover_instruction]:
            widget.bind("<Button-1>", lambda e: self.upload_cover())

        self.cover_frame.bind("<Enter>", lambda e: self.cover_frame.configure(border_color=COLOR_ACCENT_HOVER))
        self.cover_frame.bind("<Leave>", lambda e: self.cover_frame.configure(border_color=COLOR_ACCENT))

        # Upload button
        ctk.CTkButton(
            frame,
            text="Browse for Image",
            height=35,
            fg_color=COLOR_BG_DARK,
            border_color=COLOR_BORDER,
            border_width=1,
            command=self.upload_cover
        ).pack(fill="x")

    def create_lyrics_section(self):
        """Create lyrics input section"""
        frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15), padx=5)

        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            header_frame,
            text="Lyrics",
            font=("Arial", 14, "bold"),
            text_color=COLOR_TEXT
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="i",
            width=24,
            height=24,
            corner_radius=12,
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT,
            font=("Arial", 12, "bold"),
            command=self.show_lyrics_info
        ).pack(side="right")

        self.lyrics_textbox = ctk.CTkTextbox(
            frame,
            height=150,
            border_color=COLOR_BORDER,
            font=("Arial", 11)
        )
        self.lyrics_textbox.pack(fill="x")
        self.lyrics_textbox.insert("0.0", "Enter your lyrics here...\n\nUse [verse], [chorus], [bridge], [instrumental] tags to structure your song.")
        self.lyrics_textbox.edit_modified(False)

        # Warning: Minimum 15 words required
        ctk.CTkLabel(
            frame,
            text="15 words minimum",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(5, 0))

    def create_style_section(self):
        """Create style selection section - Manual mode only"""
        frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15), padx=5)

        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            header_frame,
            text="Style",
            font=("Arial", 14, "bold"),
            text_color=COLOR_TEXT
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="Surprise Me",
            height=28,
            width=120,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=("Arial", 11),
            command=self.random_style
        ).pack(side="right")

        # Manual mode: Text entry (combines Style + Genre + Type)
        ctk.CTkLabel(
            frame,
            text="Describe style, genre, and type:",
            font=("Arial", 11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 5))

        self.style_manual_entry = ctk.CTkEntry(
            frame,
            placeholder_text="e.g., Dark atmospheric rock with heavy guitars, sad and emotional",
            height=40,
            border_color=COLOR_BORDER,
            font=("Arial", 12)
        )
        self.style_manual_entry.pack(fill="x")

    def create_audio_length_section(self):
        """Create audio length selection section"""
        frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(
            frame,
            text="Audio Length",
            font=("Arial", 14, "bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 5))

        self.audio_length_var = ctk.DoubleVar(value=4.0)
        self.audio_length_slider = ctk.CTkSlider(
            frame,
            from_=0.5,
            to=10.0,
            number_of_steps=19,
            variable=self.audio_length_var,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.audio_length_slider.pack(fill="x", pady=(5, 0))
        self.audio_length_value_label = ctk.CTkLabel(
            frame,
            text="4 min 0 sec",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.audio_length_value_label.pack(anchor="e")

        # Bind slider update to value label
        self.audio_length_slider.configure(command=lambda v: self.update_audio_length_label(v))

    def create_advanced_section(self):
        """Create advanced options section"""
        self.advanced_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.advanced_frame.pack(fill="x", pady=(0, 15), padx=5)

        self.advanced_header = ctk.CTkButton(
            self.advanced_frame,
            text="Advanced Options",
            height=30,
            fg_color="transparent",
            border_width=0,
            font=("Arial", 12, "bold"),
            text_color=COLOR_TEXT,
            command=self.toggle_advanced
        )
        self.advanced_header.pack(fill="x", pady=(0, 5))

        self.advanced_content = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")

        ctk.CTkLabel(
            self.advanced_content,
            text="Model Version",
            font=("Arial", 12),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(5, 0))

        self.version_var = ctk.StringVar(value="3B")
        ctk.CTkOptionMenu(
            self.advanced_content,
            variable=self.version_var,
            values=["3B", "1B", "8B"],
            height=30,
            fg_color=COLOR_BG_DARK,
            button_color=COLOR_BORDER
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.advanced_content,
            text="Model Path",
            font=("Arial", 12),
            text_color=COLOR_TEXT
        ).pack(anchor="w")

        self.model_path_entry = ctk.CTkEntry(
            self.advanced_content,
            placeholder_text="./ckpt",
            height=30,
            border_color=COLOR_BORDER
        )
        self.model_path_entry.insert(0, "./ckpt")
        self.model_path_entry.pack(fill="x", pady=(0, 20))

        # Top-k sampling parameter
        ctk.CTkLabel(
            self.advanced_content,
            text="Top-k Sampling",
            font=("Arial", 12),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(5, 0))

        self.topk_var = ctk.DoubleVar(value=50)
        self.topk_slider = ctk.CTkSlider(
            self.advanced_content,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.topk_var,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.topk_slider.pack(fill="x", pady=(5, 0))
        self.topk_value_label = ctk.CTkLabel(
            self.advanced_content,
            text="50",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.topk_value_label.pack(anchor="e")

        # Temperature
        ctk.CTkLabel(
            self.advanced_content,
            text="Temperature",
            font=("Arial", 12),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(15, 0))

        self.temperature_var = ctk.DoubleVar(value=1.0)
        self.temperature_slider = ctk.CTkSlider(
            self.advanced_content,
            from_=0.1,
            to=2.0,
            number_of_steps=19,
            variable=self.temperature_var,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.temperature_slider.pack(fill="x", pady=(5, 0))
        self.temperature_value_label = ctk.CTkLabel(
            self.advanced_content,
            text="1.0",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.temperature_value_label.pack(anchor="e")

        # CFG Scale
        ctk.CTkLabel(
            self.advanced_content,
            text="CFG Scale",
            font=("Arial", 12),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(15, 0))

        self.cfg_scale_var = ctk.DoubleVar(value=1.5)
        self.cfg_scale_slider = ctk.CTkSlider(
            self.advanced_content,
            from_=1.0,
            to=5.0,
            number_of_steps=40,
            variable=self.cfg_scale_var,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.cfg_scale_slider.pack(fill="x", pady=(5, 0))
        self.cfg_scale_value_label = ctk.CTkLabel(
            self.advanced_content,
            text="1.5",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.cfg_scale_value_label.pack(anchor="e")

        # Bind slider updates to value labels
        self.topk_slider.configure(command=lambda v: self.topk_value_label.configure(text=f"{int(float(v))}"))
        self.temperature_slider.configure(command=lambda v: self.temperature_value_label.configure(text=f"{float(v):.1f}"))
        self.cfg_scale_slider.configure(command=lambda v: self.cfg_scale_value_label.configure(text=f"{float(v):.1f}"))

        # Progress frame
        self.progress_frame = ctk.CTkFrame(self.advanced_content, fg_color="transparent")

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Generating...",
            font=("Arial", 11),
            text_color=COLOR_ACCENT
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=8,
            corner_radius=4,
            progress_color=COLOR_ACCENT
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 5))

        self.progress_percent = ctk.CTkLabel(
            self.progress_frame,
            text="0%",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.progress_percent.pack(anchor="e")

    def create_generate_button(self):
        """Create the main generate button"""
        self.generate_btn = ctk.CTkButton(
            self.sidebar_scroll,
            text="Generate Song",
            height=50,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=("Arial", 16, "bold"),
            border_width=2,
            border_color=COLOR_ACCENT_HOVER,
            command=self.generate_song
        )
        self.generate_btn.pack(fill="x", pady=(10, 20), padx=5)

    # ==================== MAIN CONTENT ====================

    def create_main_content(self):
        """Create main content area"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(1, 0))

        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header_frame,
            text="Your Songs",
            font=("Arial", 20, "bold"),
            text_color=COLOR_TEXT
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="Refresh",
            width=35,
            height=35,
            fg_color=COLOR_BG_LIGHT,
            border_color=COLOR_BORDER,
            border_width=1,
            font=("Arial", 12),
            command=self.load_existing_songs
        ).pack(side="right")

        self.song_scroll = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="transparent",
            scrollbar_fg_color=COLOR_BG_DARK
        )
        self.song_scroll.pack(expand=True, fill="both", padx=15, pady=(0, 15))

        self.empty_state = ctk.CTkLabel(
            self.song_scroll,
            text="No songs generated yet.\nCreate your first song!",
            font=("Arial", 14),
            text_color=COLOR_TEXT_MUTED
        )
        self.empty_state.pack(pady=100)

    # ==================== BOTTOM PLAYER ====================

    def create_bottom_player(self):
        """Create bottom audio player bar"""
        self.player_frame = ctk.CTkFrame(
            self,
            height=95,
            corner_radius=0,
            fg_color=COLOR_BG_LIGHT,
            border_color=COLOR_BORDER,
            border_width=1
        )
        self.player_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.player_frame.grid_columnconfigure(1, weight=1)
        self.player_frame.grid_columnconfigure(4, weight=1)

        # Cover
        self.player_cover = ctk.CTkLabel(
            self.player_frame,
            text="",
            width=60,
            height=60,
            corner_radius=8,
            fg_color=COLOR_BG_DARK,
            font=("Arial", 24)
        )
        self.player_cover.grid(row=0, column=0, padx=15, pady=10)

        # Info
        self.player_info = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        self.player_info.grid(row=0, column=1, padx=15, pady=10, sticky="w")

        self.player_title = ctk.CTkLabel(
            self.player_info,
            text="Not Playing",
            font=("Arial", 12, "bold"),
            text_color=COLOR_TEXT
        )
        self.player_title.pack(anchor="w")

        self.player_status = ctk.CTkLabel(
            self.player_info,
            text="Select a song to play",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.player_status.pack(anchor="w")

        # Controls
        controls_frame = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=2, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="Previous",
            width=40,
            height=40,
            fg_color="transparent",
            border_width=0,
            font=("Arial", 14),
            command=self.previous_song
        ).pack(side="left", padx=5)

        self.play_btn = ctk.CTkButton(
            controls_frame,
            text="▶",
            width=50,
            height=50,
            corner_radius=25,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=("Arial", 24, "bold"),
            command=self.toggle_playback
        )
        self.play_btn.pack(side="left", padx=10)

        ctk.CTkButton(
            controls_frame,
            text="Next",
            width=40,
            height=40,
            fg_color="transparent",
            border_width=0,
            font=("Arial", 14),
            command=self.next_song
        ).pack(side="left", padx=5)

        # Progress
        progress_frame = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        progress_frame.grid(row=0, column=3, padx=20, pady=10, sticky="ew")

        self.time_label = ctk.CTkLabel(
            progress_frame,
            text="0:00 / 0:00",
            font=("Arial", 10),
            text_color=COLOR_TEXT_MUTED
        )
        self.time_label.pack(anchor="e", pady=(0, 2))

        self.seek_bar = ctk.CTkSlider(
            progress_frame,
            height=6,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            progress_color=COLOR_ACCENT,
            from_=0,
            to=100,
            command=self.seek_audio
        )
        self.seek_bar.pack(fill="x")

    # ==================== HELPER METHODS ====================

    def update_audio_length_label(self, value):
        """Update the audio length label with minutes and seconds"""
        minutes = int(float(value))
        seconds = int((float(value) - minutes) * 60)
        self.audio_length_value_label.configure(text=f"{minutes} min {seconds} sec")

    def toggle_advanced(self):
        """Toggle advanced options visibility"""
        if self.advanced_content.winfo_viewable():
            self.advanced_content.pack_forget()
            self.advanced_header.configure(text="Advanced Options")
        else:
            self.advanced_content.pack(fill="x", after=self.advanced_header)
            self.advanced_header.configure(text="Advanced Options")

    def show_lyrics_info(self):
        """Show lyrics tags information"""
        info_text = """Lyrics Tags:
- [verse] - Verse section
- [chorus] - Chorus section
- [bridge] - Bridge section
- [outro] - Ending section
- [instrumental] - Instrumental break

Example:
[verse]
Walking down the street
[chorus]
Every step I take
[instrumental]
"""
        popup = ctk.CTkToplevel(self)
        popup.title("Lyrics Guide")
        popup.geometry("350x300")
        popup.transient(self)
        popup.grab_set()
        popup.geometry("+%d+%d" % (self.winfo_x() + APP_WIDTH // 2 - 175,
                                   self.winfo_y() + APP_HEIGHT // 2 - 150))

        ctk.CTkLabel(popup, text=info_text, font=("Arial", 11), justify="left",
                     padx=20, pady=20).pack()
        ctk.CTkButton(popup, text="Got it!", command=popup.destroy, width=100).pack(pady=(0, 20))

    def random_style(self):
        """Select random style and fill in manual entry"""
        import random

        parts = []

        # Random style
        styles = list(self.styles_db.get("styles", {}).keys())
        if styles:
            style = random.choice(styles)
            substyles = self.styles_db["styles"][style]
            if substyles:
                parts.append(f"{style} {random.choice(substyles)}")
            else:
                parts.append(style)

        # Random genre
        genres = list(self.styles_db.get("genres", {}).keys())
        if genres:
            parts.append(random.choice(genres))

        # Random type
        types = list(self.styles_db.get("types", {}).keys())
        if types:
            song_type = random.choice(types)
            subtypes = self.styles_db["types"][song_type]
            if subtypes:
                parts.append(f"{song_type} {random.choice(subtypes)}")
            else:
                parts.append(song_type)

        # Fill in manual entry
        if hasattr(self, 'style_manual_entry'):
            self.style_manual_entry.delete(0, "end")
            self.style_manual_entry.insert(0, ", ".join(parts))

    # ==================== COVER ART METHODS ====================

    def upload_cover(self):
        """Upload cover art image"""
        filepath = filedialog.askopenfilename(
            title="Select Cover Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")]
        )
        if filepath:
            try:
                img = Image.open(filepath)
                self.process_dropped_image(img)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

    def process_dropped_image(self, img):
        """Process and crop image to square"""
        try:
            width, height = img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            img = img.crop((left, top, left + size, top + size))
            img = img.resize((500, 500), Image.Resampling.LANCZOS)

            self.current_cover_path = str(self.file_manager.covers_dir / "temp_cover.png")
            img.save(self.current_cover_path)

            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 140))
            self.cover_label.configure(image=photo, text="")
            self.cover_label.image = photo
            self.cover_instruction.configure(text="")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process image: {e}")

    def generate_random_gradient_cover(self, title):
        """Generate a 200x200px random gradient cover image"""
        import random

        # Create a 200x200px image with random gradient
        width, height = 200, 200
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        # Generate random colors for gradient
        color1 = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        color2 = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        # Create diagonal gradient
        for y in range(height):
            for x in range(width):
                # Calculate gradient position (diagonal from top-left to bottom-right)
                ratio = (x + y) / (width + height - 2)
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                pixels[x, y] = (r, g, b)

        # Save the image
        cover_path = str(self.file_manager.covers_dir / f"{title}.png")
        img.save(cover_path)
        return cover_path

    # ==================== GENERATION METHODS ====================

    def generate_song(self):
        """Generate a new song"""
        if self.generating:
            return

        title = self.title_entry.get().strip()
        if not title:
            title = self.file_manager.get_next_unknown_name()
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, title)

        lyrics = self.lyrics_textbox.get("0.0", "end").strip()
        if lyrics.startswith("Enter your lyrics here"):
            lyrics = ""

        # Manual mode - get style from text entry (includes genre and type)
        full_style = self.style_manual_entry.get().strip()
        genre = ""  # Genre is included in manual text
        full_type = ""  # Type is included in manual text

        model_path = self.model_path_entry.get().strip() or "./ckpt"
        version = self.version_var.get()
        
        # Get advanced parameters
        topk = int(self.topk_var.get())
        temperature = float(self.temperature_var.get())
        cfg_scale = float(self.cfg_scale_var.get())
        audio_length_ms = int(self.audio_length_var.get() * 60 * 1000)  # Convert minutes to milliseconds

        self.generating = True
        self.current_title = title
        self.generate_btn.configure(state="disabled", text="Generating...")

        self.progress_frame.pack(fill="x", pady=10, after=self.model_path_entry)
        self.progress_bar.set(0)
        self.progress_percent.configure(text="0%")

        thread = threading.Thread(
            target=self.run_generation,
            args=(title, lyrics, full_style, genre, full_type, model_path, version, topk, temperature, cfg_scale, audio_length_ms)
        )
        thread.daemon = True
        thread.start()

    def run_generation(self, title, lyrics, style, genre, song_type, model_path, version, topk, temperature, cfg_scale, audio_length_ms):
        """Execute music generation command"""
        try:
            # Sanitize title for file paths - remove special characters
            import re
            safe_title = re.sub(r'[^\w\s-]', '_', title)
            safe_title = safe_title.strip()
            if not safe_title:
                safe_title = "song"
            
            # Get assets directory
            assets_dir = self.file_manager.base_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                sys.executable,
                "./examples/run_music_generation.py",
                f"--model_path={model_path}",
                f"--version={version}"
            ]

            save_path = str(self.file_manager.songs_dir / f"{safe_title}.wav")
            cmd.append(f"--save_path={save_path}")

            # Add advanced parameters
            cmd.append(f"--topk={topk}")
            cmd.append(f"--temperature={temperature}")
            cmd.append(f"--cfg_scale={cfg_scale}")
            cmd.append(f"--max_audio_length_ms={audio_length_ms}")

            # Write lyrics directly to assets folder (model may have hardcoded path)
            lyrics_path = str(assets_dir / "lyrics.txt")
            if lyrics:
                with open(lyrics_path, 'w', encoding='utf-8') as f:
                    f.write(lyrics)
                cmd.append("--lyrics=assets/lyrics.txt")  # Use relative path
                print(f"[HeartMuLa] Wrote lyrics to: {lyrics_path}")
                print(f"[HeartMuLa] Lyrics preview: {lyrics[:80]}...")

            # Build tags from manual description (includes style, genre, and type)
            tags_parts = []
            if style:
                tags_parts.append(style)

            # Write tags directly to assets folder
            tags_path = str(assets_dir / "tags.txt")
            if tags_parts:
                with open(tags_path, 'w', encoding='utf-8') as f:
                    f.write(",".join(tags_parts))
                cmd.append("--tags=assets/tags.txt")  # Use relative path
                print(f"[HeartMuLa] Wrote tags to: {tags_path}")
                print(f"[HeartMuLa] Tags: {tags_parts}")

            print(f"[HeartMuLa] Running: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            total_steps = 100
            current_step = 0

            for line in process.stdout:
                line = line.strip()
                if "step" in line.lower() or "generating" in line.lower() or "progress" in line.lower():
                    current_step = min(current_step + 2, total_steps)
                    self.after(0, lambda p=current_step/total_steps: self.update_generation_progress(p, line))
                print(f"[HeartMuLa] {line}")

            process.wait()

            if process.returncode == 0:
                expected_file = Path(save_path)
                if not expected_file.exists():
                    wav_files = sorted(self.file_manager.songs_dir.glob("*.wav"),
                                      key=lambda f: f.stat().st_mtime, reverse=True)
                    if wav_files:
                        expected_file = wav_files[0]

                cover_path = None
                if self.current_cover_path:
                    final_cover_path = str(self.file_manager.covers_dir / f"{title}.png")
                    if os.path.exists(self.current_cover_path):
                        os.rename(self.current_cover_path, final_cover_path)
                    cover_path = final_cover_path
                else:
                    # Generate random gradient cover if no image uploaded
                    cover_path = self.generate_random_gradient_cover(title)

                self.file_manager.save_metadata(title, lyrics, style, genre, song_type, cover_path)

                # Clean up temporary files
                try:
                    temp_lyrics = self.file_manager.output_dir / f"temp_lyrics_{safe_title}.txt"
                    temp_tags = self.file_manager.output_dir / f"temp_tags_{safe_title}.txt"
                    if temp_lyrics.exists():
                        temp_lyrics.unlink()
                    if temp_tags.exists():
                        temp_tags.unlink()
                except:
                    pass

                self.after(0, lambda: self.generation_complete(True))
            else:
                self.after(0, lambda: self.generation_complete(False))

        except Exception as e:
            print(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self.generation_complete(False))

    def update_generation_progress(self, progress, status_text):
        """Update progress bar"""
        self.progress_bar.set(progress)
        self.progress_percent.configure(text=f"{int(progress * 100)}%")
        if status_text:
            self.progress_label.configure(text=status_text[:50] + "..." if len(status_text) > 50 else status_text)

    def generation_complete(self, success):
        """Handle generation completion"""
        self.generating = False
        self.generate_btn.configure(state="normal", text="Generate Song")

        if success:
            self.after(2000, lambda: self.progress_frame.pack_forget())

            self.title_entry.delete(0, "end")
            self.lyrics_textbox.delete("0.0", "end")
            self.lyrics_textbox.insert("0.0", "Enter your lyrics here...\n\nUse [verse], [chorus], [bridge], [instrumental] tags to structure your song.")
            self.lyrics_textbox.edit_modified(False)

            # Clear manual style entry
            if hasattr(self, 'style_manual_entry'):
                self.style_manual_entry.delete(0, "end")

            self.current_cover_path = None
            self.cover_label.configure(image=None, text="+")
            self.cover_label.image = None
            self.cover_instruction.configure(text="Click to browse")

            self.load_existing_songs()
            messagebox.showinfo("Success", f"Song '{self.current_title}' generated successfully!")
        else:
            messagebox.showerror("Error", "Failed to generate song. Check console.")

    # ==================== SONG LIST METHODS ====================

    def load_existing_songs(self):
        """Load and display existing songs"""
        songs = self.file_manager.get_all_songs()

        if not songs:
            self.empty_state.pack(pady=100)
            for widget in self.song_scroll.winfo_children():
                if widget != self.empty_state:
                    widget.destroy()
            return

        self.empty_state.pack_forget()
        for widget in self.song_scroll.winfo_children():
            widget.destroy()

        self.playlist = songs
        for i, song in enumerate(songs):
            self.create_song_card(song, i)
        
        # Restore play overlay if audio is playing
        if pygame.mixer.music.get_busy() and self.current_playlist_index >= 0:
            if self.current_playlist_index < len(self.playlist):
                song = self.playlist[self.current_playlist_index]
                if "play_overlay" in song and song["play_overlay"]:
                    try:
                        song["play_overlay"].configure(text="▶")
                    except:
                        pass

    def create_song_card(self, song, index):
        """Create a song card widget"""
        card = ctk.CTkFrame(
            self.song_scroll,
            fg_color=COLOR_BG_LIGHT,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=12
        )
        card.pack(fill="x", pady=8, padx=5)
        card.grid_columnconfigure(1, weight=1)

        # Cover - Clickable to play
        cover_frame = ctk.CTkFrame(card, width=100, height=100, corner_radius=10, fg_color=COLOR_BG_DARK)
        cover_frame.grid(row=0, column=0, padx=10, pady=10)
        cover_frame.grid_propagate(False)

        cover_label = ctk.CTkLabel(cover_frame, text="", font=("Arial", 36), text_color=COLOR_TEXT_MUTED)
        cover_label.place(relx=0.5, rely=0.5, anchor="center")

        if os.path.exists(song["cover_path"]):
            try:
                img = Image.open(song["cover_path"])
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                cover_label.configure(image=photo, text="")
                cover_label.image = photo
            except:
                pass

        # Play symbol overlay (hidden by default)
        play_overlay = ctk.CTkLabel(cover_frame, text="▶", font=("Arial", 36), text_color=COLOR_TEXT, fg_color="transparent")
        play_overlay.place(relx=0.5, rely=0.5, anchor="center")
        play_overlay.configure(text="")  # Hidden by default
        
        # Make cover clickable
        cover_frame.bind("<Button-1>", lambda e: self.play_song(index))
        cover_label.bind("<Button-1>", lambda e: self.play_song(index))
        play_overlay.bind("<Button-1>", lambda e: self.play_song(index))
        
        # Store reference to overlay for updating
        song["play_overlay"] = play_overlay

        # Info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nw")

        metadata = song.get("metadata", {})
        style_info = metadata.get("style", "Unknown Style")
        genre_info = metadata.get("genre", "")
        type_info = metadata.get("type", "")

        info_text = style_info
        if genre_info:
            info_text += f" | {genre_info}"
        if type_info:
            info_text += f" | {type_info}"

        ctk.CTkLabel(info_frame, text=song["title"], font=("Arial", 14, "bold"),
                     text_color=COLOR_TEXT).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=info_text, font=("Arial", 11),
                     text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        if os.path.exists(song["wav_path"]):
            file_size = os.path.getsize(song["wav_path"])
            duration = file_size / 44100 / 4
            mins, secs = int(duration // 60), int(duration % 60)
            duration_text = f"{mins}:{secs:02d}"
        else:
            duration_text = "?:??"

        ctk.CTkLabel(info_frame, text=f"Duration: {duration_text}", font=("Arial", 10),
                     text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        # Menu dropdown
        self.song_menu_var = ctk.StringVar(value="...")
        self.song_menu = ctk.CTkOptionMenu(
            card,
            values=["Remix / Edit", "Song Details", "Download", "Move To Trash"],
            variable=self.song_menu_var,
            width=35,
            height=35,
            fg_color=COLOR_BG,
            button_color=COLOR_BG,
            button_hover_color=COLOR_BG_LIGHT,
            dropdown_fg_color=COLOR_BG_LIGHT,
            dropdown_hover_color=COLOR_ACCENT,
            font=("Arial", 18),
            dynamic_resizing=False,
            command=lambda value: self.handle_song_menu_action(value, song)
        )
        self.song_menu.set("...")
        self.song_menu.grid(row=0, column=2, padx=10, pady=10)

    def handle_song_menu_action(self, action, song):
        """Handle song menu selection"""
        self.song_menu.set("...")  # Reset to ...
        if action == "Remix / Edit":
            self.remix_song(song)
        elif action == "Song Details":
            self.show_song_details(song)
        elif action == "Download":
            self.download_song(song)
        elif action == "Move To Trash":
            self.delete_song(song)

    def remix_song(self, song):
        """Load song settings for editing"""
        metadata = song.get("metadata", {})
        if not metadata:
            return

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, f"{song['title']} (Remix)")

        self.lyrics_textbox.delete("0.0", "end")
        self.lyrics_textbox.insert("0.0", metadata.get("lyrics", ""))
        self.lyrics_textbox.edit_modified(False)

        # Load style (includes genre and type in manual mode)
        style_full = metadata.get("style", "")
        if hasattr(self, 'style_manual_entry'):
            self.style_manual_entry.delete(0, "end")
            # Also include genre and type if they exist
            genre = metadata.get("genre", "")
            type_full = metadata.get("type", "")
            full_desc = style_full
            if genre:
                full_desc = f"{full_desc}, {genre}" if full_desc else genre
            if type_full:
                full_desc = f"{full_desc}, {type_full}" if full_desc else type_full
            self.style_manual_entry.insert(0, full_desc)

        cover_path = metadata.get("cover_path")
        if cover_path and os.path.exists(cover_path):
            try:
                img = Image.open(cover_path)
                img = img.resize((500, 500), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 140))
                self.cover_label.configure(image=photo, text="")
                self.cover_label.image = photo
                self.cover_instruction.configure(text="")
                self.current_cover_path = cover_path
            except:
                pass

    def show_song_details(self, song):
        """Show song details"""
        metadata = song.get("metadata", {})
        if not metadata:
            return

        details = f"""Song Title: {song['title']}

Style: {metadata.get('style', 'N/A')}
Genre: {metadata.get('genre', 'N/A')}
Type: {metadata.get('type', 'N/A')}

Lyrics:
{metadata.get('lyrics', 'No lyrics provided')}

Created: {metadata.get('created_at', 'Unknown')}

Files:
- Audio: {os.path.basename(song['wav_path'])}
- Cover: {os.path.basename(metadata.get('cover_path', 'N/A'))}
"""

        popup = ctk.CTkToplevel(self)
        popup.title(f"Song Details - {song['title']}")
        popup.geometry("500x500")
        popup.transient(self)

        textbox = ctk.CTkTextbox(popup, font=("Arial", 11))
        textbox.pack(expand=True, fill="both", padx=15, pady=15)
        textbox.insert("0.0", details)
        textbox.configure(state="disabled")
        ctk.CTkButton(popup, text="Close", command=popup.destroy, width=100).pack(pady=(0, 15))

    def download_song(self, song):
        """Download song to user location"""
        if not os.path.exists(song["wav_path"]):
            messagebox.showerror("Error", "Audio file not found!")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Song As",
            defaultextension=".wav",
            initialfile=f"{song['title']}.wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )

        if save_path:
            try:
                import shutil
                shutil.copy2(song["wav_path"], save_path)
                messagebox.showinfo("Success", f"Song saved to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save:\n{e}")

    def delete_song(self, song):
        """Delete song files"""
        if messagebox.askyesno("Confirm Delete", f"Delete '{song['title']}'?\n\nThis cannot be undone."):
            self.file_manager.delete_song_files(song["title"])
            self.load_existing_songs()

    # ==================== AUDIO PLAYBACK ====================

    def play_song(self, index):
        """Play a song from the playlist"""
        if index >= len(self.playlist):
            return

        self.current_playlist_index = index
        song = self.playlist[index]

        # Hide all play overlays first
        for s in self.playlist:
            if "play_overlay" in s and s["play_overlay"]:
                try:
                    s["play_overlay"].configure(text="")
                except:
                    pass

        # Show play overlay on this song
        if "play_overlay" in song and song["play_overlay"]:
            try:
                song["play_overlay"].configure(text="▶")
            except:
                pass

        try:
            pygame.mixer.music.load(song["wav_path"])
            pygame.mixer.music.play()
            self.update_player_ui(song)
        except Exception as e:
            print(f"Error playing: {e}")

    def toggle_playback(self):
        """Toggle play/pause"""
        # If no song is selected or playlist is empty, play the last song
        if not self.playlist:
            return
        
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.play_btn.configure(text="▶")
            # Hide play overlay
            if (self.current_playlist_index >= 0 and 
                self.current_playlist_index < len(self.playlist)):
                song = self.playlist[self.current_playlist_index]
                if "play_overlay" in song and song["play_overlay"]:
                    try:
                        song["play_overlay"].configure(text="")
                    except:
                        pass
        else:
            # If no song is currently selected, play the last one
            if self.current_playlist_index >= len(self.playlist) or self.current_playlist_index < 0:
                self.current_playlist_index = len(self.playlist) - 1
            
            if self.current_playlist_index >= 0 and self.current_playlist_index < len(self.playlist):
                song = self.playlist[self.current_playlist_index]
                try:
                    pygame.mixer.music.load(song["wav_path"])
                    pygame.mixer.music.play()
                    self.update_player_ui(song)
                except Exception as e:
                    print(f"Error playing: {e}")

    def previous_song(self):
        """Play previous song"""
        if self.playlist:
            new_index = (self.current_playlist_index - 1) % len(self.playlist)
            self.play_song(new_index)

    def next_song(self):
        """Play next song"""
        if self.playlist:
            new_index = (self.current_playlist_index + 1) % len(self.playlist)
            self.play_song(new_index)

    def seek_audio(self, value):
        """Seek to position"""
        try:
            position = (value / 100) * pygame.mixer.Sound(self.playlist[self.current_playlist_index]["wav_path"]).get_length()
            pygame.mixer.music.play(start=position)
        except:
            pass

    def update_player_ui(self, song):
        """Update the bottom player"""
        if song:
            self.player_title.configure(text=song["title"])
            self.player_status.configure(text="Now Playing")
            self.play_btn.configure(text="■")

            if os.path.exists(song["cover_path"]):
                try:
                    img = Image.open(song["cover_path"])
                    img = img.resize((60, 60), Image.Resampling.LANCZOS)
                    photo = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 60))
                    self.player_cover.configure(image=photo, text="")
                    self.player_cover.image = photo
                except:
                    pass
        else:
            self.player_title.configure(text="Not Playing")
            self.player_status.configure(text="Select a song")
            self.play_btn.configure(text="▶")
            self.player_cover.configure(image=None, text="")

    def update_audio_ui(self):
        """Update audio progress"""
        try:
            if pygame.mixer.music.get_busy() and self.playlist:
                song = self.playlist[self.current_playlist_index]
                if os.path.exists(song["wav_path"]):
                    sound = pygame.mixer.Sound(song["wav_path"])
                    length = sound.get_length()
                    position = pygame.mixer.music.get_pos() / 1000

                    progress = (position / length) * 100
                    self.seek_bar.set(progress)

                    cur_mins, cur_secs = int(position // 60), int(position % 60)
                    tot_mins, tot_secs = int(length // 60), int(length % 60)
                    self.time_label.configure(text=f"{cur_mins}:{cur_secs:02d} / {tot_mins}:{tot_secs:02d}")

                    if position >= length - 0.5:
                        self.next_song()
        except:
            pass

        self.after(100, self.update_audio_ui)

    def destroy(self):
        """Cleanup on close"""
        pygame.mixer.quit()
        super().destroy()


def main():
    """Main entry point"""
    app = HeartMuLaStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
