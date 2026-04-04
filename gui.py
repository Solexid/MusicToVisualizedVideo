#!/usr/bin/env python3
"""
GUI entry point for Music To Visualized Video converter.
Uses Tkinter for the user interface.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font
import threading
import os
from pathlib import Path

from core import MP3ToVideoConverter


class ConverterGUI:
    """GUI for MP3 to Video converter."""
    
    # Dark theme colors
    BG_DARK = "#1a1a2e"
    BG_MEDIUM = "#16213e"
    BG_LIGHT = "#0f3460"
    ACCENT = "#97829e"
    ACCENT_HOVER = "#3D194A"
    START_BTN = "#27ae60"
    START_BTN_HOVER = "#2ecc71"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"
    ENTRY_BG = "#2a2a3e"
    ENTRY_FG = "#ffffff"
    SUCCESS = "#00d26a"
    
    VISUALIZATION_TYPES = [
        ("Sphere (GEQ)", 0),
        ("Lines", 1),
        ("Bottom Full-Width", 2),
        ("Top/Bottom", 3),
        ("Vectorscope", 4),
        ("Circular (GLSL)", 5)
    ]
    
    def __init__(self, root):
        self.root = root
        self.root.title("Music To Visualized Video")
        self.root.geometry("900x650")
        self.root.minsize(800, 580)
        self.root.configure(bg=self.BG_DARK)
        
        # Configure style
        self._configure_style()
        
        self.converter = None
        self.processing = False
        self.stop_flag = False
        self._create_widgets()
        self._load_settings()
    
    def _configure_style(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', 
            background=self.BG_DARK,
            foreground=self.TEXT_PRIMARY,
            fieldbackground=self.ENTRY_BG
        )
        
        style.configure('TFrame', background=self.BG_DARK)
        style.configure('Main.TFrame', background=self.BG_DARK)
        style.configure('Settings.TFrame', background=self.BG_MEDIUM)
        style.configure('TLabel',
            background=self.BG_DARK,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10)
        )
        style.configure('Settings.TLabel',
            background=self.BG_MEDIUM,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 9)
        )
        
        style.configure('TButton',
            background=self.BG_LIGHT,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            padding=(20, 8)
        )

        style.map('TButton',
            background=[('active', self.ACCENT), ('pressed', self.ACCENT_HOVER)]
        )

        style.configure('Accent.TButton',
            background=self.ACCENT,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            padding=(20, 8)
        )

        style.map('Accent.TButton',
            background=[('active', self.ACCENT_HOVER), ('pressed', self.ACCENT)]
        )

        style.configure('Danger.TButton',
            background='#c0392b',
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            padding=(20, 8)
        )

        style.map('Danger.TButton',
            background=[('active', '#e74c3c'), ('pressed', '#c0392b')]
        )

        style.configure('Start.TButton',
            background=self.START_BTN,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            padding=(20, 8)
        )

        style.map('Start.TButton',
            background=[('active', self.START_BTN_HOVER), ('pressed', self.START_BTN)]
        )

        style.configure('TLabelframe',
            background=self.BG_MEDIUM,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 11, 'bold')
        )
        
        style.configure('TLabelframe.Label',
            background=self.BG_MEDIUM,
            foreground=self.ACCENT,
            font=('Segoe UI', 11, 'bold')
        )
        
        style.configure('TCheckbutton',
            background=self.BG_DARK,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 10)
        )

        style.map('TCheckbutton',
            background=[('active', self.BG_DARK)]
        )

        style.configure('Settings.TCheckbutton',
            background=self.BG_MEDIUM,
            foreground=self.TEXT_PRIMARY,
            font=('Segoe UI', 9)
        )

        style.map('Settings.TCheckbutton',
            background=[('active', self.BG_MEDIUM)]
        )
        
        style.configure('Horizontal.TProgressbar',
            background=self.ACCENT,
            troughcolor=self.BG_MEDIUM,
            borderwidth=0,
            lightcolor=self.ACCENT,
            darkcolor=self.ACCENT
        )
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.configure(style='Main.TFrame')

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Two equal columns for main content
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = tk.Label(
            main_frame,
            text="🎵 Music To Visualized Video",
            font=('Segoe UI', 18, 'bold'),
            bg=self.BG_DARK,
            fg=self.ACCENT
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # === LEFT COLUMN - Folders, Log ===
        left_frame = ttk.Frame(main_frame, style='Main.TFrame')
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)

        # Input folder row
        input_row = ttk.Frame(left_frame, style='Main.TFrame')
        input_row.grid(row=0, column=0, sticky="ew", pady=4)
        input_row.columnconfigure(1, weight=1)

        ttk.Label(input_row, text="📁 Input:", width=8).pack(side="left")
        self.input_var = tk.StringVar()
        ttk.Entry(input_row, textvariable=self.input_var, font=('Segoe UI', 9)).pack(side="left", fill=tk.X, expand=True, padx=5)
        ttk.Button(input_row, text="Browse...", command=self._browse_input).pack(side="right")

        # Output folder row
        output_row = ttk.Frame(left_frame, style='Main.TFrame')
        output_row.grid(row=1, column=0, sticky="ew", pady=4)
        output_row.columnconfigure(1, weight=1)

        ttk.Label(output_row, text="📂 Output:", width=8).pack(side="left")
        self.output_var = tk.StringVar()
        ttk.Entry(output_row, textvariable=self.output_var, font=('Segoe UI', 9)).pack(side="left", fill=tk.X, expand=True, padx=5)
        ttk.Button(output_row, text="Browse...", command=self._browse_output).pack(side="right")

        # Log - fixed height
        log_frame = ttk.LabelFrame(left_frame, text="📋 Log", padding="6")
        log_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            font=('Consolas', 9),
            bg=self.ENTRY_BG,
            fg=self.TEXT_PRIMARY,
            insertbackground=self.TEXT_PRIMARY,
            selectbackground=self.BG_LIGHT,
            relief=tk.FLAT,
            padx=8,
            pady=8,
            wrap=tk.WORD
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # === RIGHT COLUMN - Settings ===
        settings_frame = ttk.LabelFrame(main_frame, text="⚙ Settings", padding="12")
        settings_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        settings_frame.columnconfigure(0, minsize=100)  # Fixed width for labels
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.rowconfigure(10, weight=1)

        s_row = 0

        # Top section - encoding settings
        ttk.Label(settings_frame, text="Batch:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.batch_size_var = tk.IntVar(value=25)
        ttk.Spinbox(settings_frame, from_=1, to=50, width=10, textvariable=self.batch_size_var, font=('Segoe UI', 9)).grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        ttk.Label(settings_frame, text="Font:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        font_frame = ttk.Frame(settings_frame, style='Settings.TFrame')
        font_frame.grid(row=s_row, column=1, sticky="ew")
        font_frame.columnconfigure(0, weight=1)
        self.font_var = tk.StringVar(value='arial.ttf')
        ttk.Entry(font_frame, textvariable=self.font_var, width=15, font=('Segoe UI', 9)).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(font_frame, text="Browse...", command=self._browse_font, width=8).grid(row=0, column=1)
        s_row += 1

        ttk.Label(settings_frame, text="Video kbps:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.vrate_var = tk.IntVar(value=550)
        ttk.Spinbox(settings_frame, from_=100, to=5000, width=10, textvariable=self.vrate_var, font=('Segoe UI', 9)).grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        ttk.Label(settings_frame, text="Audio kbps:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.arate_var = tk.IntVar(value=192)
        ttk.Spinbox(settings_frame, from_=64, to=512, width=10, textvariable=self.arate_var, font=('Segoe UI', 9)).grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        ttk.Label(settings_frame, text="FPS:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.frate_var = tk.IntVar(value=30)
        ttk.Spinbox(settings_frame, from_=15, to=60, width=10, textvariable=self.frate_var, font=('Segoe UI', 9)).grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        ttk.Label(settings_frame, text="Codec:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.codec_var = tk.StringVar(value='libx264')
        ttk.Entry(settings_frame, textvariable=self.codec_var, width=15, font=('Segoe UI', 9)).grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        ttk.Label(settings_frame, text="Shuffle:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.shuffle_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="🔀 Shuffle tracks", variable=self.shuffle_var, style='Settings.TCheckbutton').grid(row=s_row, column=1, sticky="w", padx=5)
        s_row += 1

        # Separator before visual settings
        ttk.Separator(settings_frame, orient='horizontal').grid(row=s_row, column=0, columnspan=2, sticky="ew", pady=8)
        s_row += 1

        # Visual settings section
        ttk.Label(settings_frame, text="Visual:", style='Settings.TLabel').grid(row=s_row, column=0, sticky="e", pady=4, padx=(0, 10))
        self.vis_type_var = tk.IntVar(value=0)
        self.vis_combo = ttk.Combobox(settings_frame, values=[n for n, _ in self.VISUALIZATION_TYPES], width=20, state="readonly", font=('Segoe UI', 9))
        self.vis_combo.current(0)
        self.vis_combo.grid(row=s_row, column=1, sticky="ew", padx=5)
        self.vis_combo.bind("<<ComboboxSelected>>", self._on_vis_type_changed)
        s_row += 1

        # Colors - stacked vertically
        color_frame = ttk.Frame(settings_frame, style='Settings.TFrame')
        color_frame.grid(row=s_row, column=0, columnspan=2, sticky="w", pady=5)
        s_row += 1
        
        ttk.Label(color_frame, text="Color 1:", style='Settings.TLabel').grid(row=0, column=0, sticky="e", pady=2, padx=(0, 10))
        self.wavecolor_var = tk.StringVar()
        ttk.Entry(color_frame, textvariable=self.wavecolor_var, width=10, font=('Segoe UI', 8)).grid(row=0, column=1, padx=0)
        
        ttk.Label(color_frame, text="Color 2:", style='Settings.TLabel').grid(row=1, column=0, sticky="e", pady=2, padx=(0, 10))
        self.wavecolor2_var = tk.StringVar(value="0x9400D3")
        ttk.Entry(color_frame, textvariable=self.wavecolor2_var, width=10, font=('Segoe UI', 8)).grid(row=1, column=1, padx=0)

        # Separator before test mode
        ttk.Separator(settings_frame, orient='horizontal').grid(row=s_row, column=0, columnspan=2, sticky="ew", pady=10)
        s_row += 1

        # Test mode - alone in bottom section
        self.test_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="🧪 Test Mode", variable=self.test_mode_var, command=self._toggle_test_duration, style='Settings.TCheckbutton').grid(row=s_row, column=0, columnspan=2, sticky="w", pady=5)
        s_row += 1

        test_frame = ttk.Frame(settings_frame, style='Settings.TFrame')
        test_frame.grid(row=s_row, column=0, columnspan=2, sticky="w", pady=5, padx=(100, 0))
        ttk.Label(test_frame, text="Duration (sec):", style='Settings.TLabel').pack(side="left")
        self.test_duration_var = tk.IntVar(value=60)
        self.test_duration_spinbox = ttk.Spinbox(test_frame, from_=10, to=300, width=6, textvariable=self.test_duration_var, state="disabled", font=('Segoe UI', 8))
        self.test_duration_spinbox.pack(side="left", padx=(5, 0))

        # === BOTTOM SECTION - Progress + Buttons ===
        bottom_frame = ttk.Frame(main_frame, style='Main.TFrame')
        bottom_frame.grid(row=2, column=0, columnspan=2, pady=(10, 15), padx=10)
        
        # Progress bar - full width
        progress_bottom = ttk.Frame(bottom_frame, style='Main.TFrame')
        progress_bottom.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_bottom, variable=self.progress_var, maximum=100, length=600)
        self.progress_bar.pack(fill=tk.X, expand=True)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_bottom, textvariable=self.status_var, font=('Segoe UI', 10, 'italic')).pack(anchor="w", pady=(3, 0))
        
        # Buttons
        button_frame = ttk.Frame(bottom_frame, style='Main.TFrame')
        button_frame.pack()

        self.start_button = ttk.Button(button_frame, text="▶ Start", style='Start.TButton', command=self._start_processing)
        self.start_button.pack(side="left", padx=15)

        self.stop_button = ttk.Button(button_frame, text="⏹ Stop", style='Danger.TButton', command=self._stop_processing, state="disabled")
        self.stop_button.pack(side="left", padx=15)

        ttk.Button(button_frame, text="🗑 Clear Log", command=self._clear_log).pack(side="left", padx=15)
    
    def _toggle_test_duration(self):
        """Enable/disable test duration spinbox."""
        if self.test_mode_var.get():
            self.test_duration_spinbox.config(state="normal")
        else:
            self.test_duration_spinbox.config(state="disabled")
    
    def _browse_font(self):
        """Browse for font file."""
        filepath = filedialog.askopenfilename(
            title="Select Font File",
            filetypes=[("Font files", "*.ttf *.otf *.ttc"), ("All files", "*.*")]
        )
        if filepath:
            self.font_var.set(filepath)
    
    def _on_vis_type_changed(self, event=None):
        """Handle visualization type selection change."""
        selected_index = self.vis_combo.current()
        if 0 <= selected_index < len(self.VISUALIZATION_TYPES):
            _, vis_type = self.VISUALIZATION_TYPES[selected_index]
            self.vis_type_var.set(vis_type)
    
    def _browse_input(self):
        """Browse for input folder."""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_var.set(folder)
    
    def _browse_output(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_var.set(folder)
    
    def _load_settings(self):
        """Load default settings or from config."""
        default_out = Path.cwd() / "out"
        default_out.mkdir(exist_ok=True)
        self.output_var.set(str(default_out))
    
    def _log(self, message):
        """Add message to log."""
        timestamp = f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] "
        self.log_text.insert(tk.END, timestamp + message + "\n")
        self.log_text.see(tk.END)
    
    def _clear_log(self):
        """Clear the log."""
        self.log_text.delete(1.0, tk.END)
    
    def _update_progress(self, current, total, message=""):
        """Update progress bar and status."""
        if total > 0:
            percent = (current / total) * 100
            self.progress_var.set(percent)
        if message:
            self.status_var.set(message)
    
    def _validate_inputs(self):
        """Validate user inputs."""
        if not self.input_var.get():
            messagebox.showerror("Error", "Please select input folder")
            return False
        
        if not self.output_var.get():
            messagebox.showerror("Error", "Please select output folder")
            return False
        
        if not os.path.isdir(self.input_var.get()):
            messagebox.showerror("Error", "Input folder does not exist")
            return False
        
        return True
    
    def _start_processing(self):
        """Start the conversion process."""
        if not self._validate_inputs():
            return
        
        self.processing = True
        self.stop_flag = False
        
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self._process, daemon=True)
        thread.start()
    
    def _stop_processing(self):
        """Stop the conversion process."""
        self.stop_flag = True
        self._log("Stopping...")
        if self.converter:
            self.converter.stop()
    
    def _process(self):
        """Run the conversion process."""
        error_msg = None
        try:
            test_value = self.test_duration_var.get() if self.test_mode_var.get() else False
            
            self.converter = MP3ToVideoConverter(
                input_folder=self.input_var.get(),
                output_folder=self.output_var.get(),
                batch_size=self.batch_size_var.get(),
                arate=self.arate_var.get(),
                vrate=self.vrate_var.get(),
                font=self.font_var.get(),
                frate=self.frate_var.get(),
                codec=self.codec_var.get(),
                vis_type=self.vis_type_var.get(),
                test=test_value,
                wavecolor=self.wavecolor_var.get() if self.wavecolor_var.get() else None,
                wavecolor2=self.wavecolor2_var.get() if self.wavecolor2_var.get() else None,
                shuffle=1 if self.shuffle_var.get() else 0,
                progress_callback=self._update_progress,
                log_callback=self._log,
                use_tqdm=False
            )
            
            self.converter.process_all()
            
            self.root.after(0, lambda: messagebox.showinfo("Complete", "Processing completed successfully!"))
            
        except Exception as ex:
            error_msg = str(ex)
            if "interrupted" in error_msg.lower() or self.stop_flag:
                self.root.after(0, lambda: self._log("Process stopped by user"))
            else:
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Processing failed: {msg}"))
        finally:
            self.processing = False
            self.root.after(0, self._processing_complete)
    
    def _processing_complete(self):
        """Called when processing is complete."""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Ready")


def main():
    """Main entry point for GUI."""
    root = tk.Tk()
    root.configure(bg=ConverterGUI.BG_DARK)
    
    try:
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
    except:
        pass
    
    app = ConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
