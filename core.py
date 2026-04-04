"""
Core module for Music To Visualized Video converter.
Contains the main MP3ToVideoConverter class used by both CLI and GUI.
"""

import os
import json
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, error as ID3Error
from PIL import Image, ImageDraw, ImageFont
import subprocess
import tempfile
import chardet
import random
from tqdm import tqdm
from viz_filters import VisualizationFilters


class MP3ToVideoConverter:
    """Main converter class for converting MP3 files to videos with visualizations."""
    
    def __init__(self, input_folder, output_folder, batch_size=25, arate=192, vrate=550,
                 font='arial.ttf', shuffle=0, frate=30, codec='libx264', vis_type=0,
                 test=False, wavecolor=None, wavecolor2=None, afreq=44100,
                 progress_callback=None, log_callback=None, use_tqdm=True, background=None):
        """
        Initialize the converter.

        Args:
            input_folder: Path to folder with MP3 files
            output_folder: Path to folder for output videos
            batch_size: Number of tracks per video batch
            arate: Audio bitrate in kbps
            vrate: Video bitrate in kbps
            font: Font file path
            shuffle: Shuffle input files (0 or 1)
            frate: Video framerate
            codec: Video codec (e.g., 'libx264', 'h264_nvenc')
            vis_type: Visualization type (0-5)
            test: Test mode - False, True (60s), or number of seconds
            wavecolor: Primary wave color (hex)
            wavecolor2: Secondary wave color (hex)
            afreq: Audio frequency in Hz
            progress_callback: Optional callback for progress updates (current, total, message)
            log_callback: Optional callback for log messages
            use_tqdm: Use tqdm progress bar in CLI (default: True)
            background: Background image path or hex color (None = use album art)
        """
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        tempfile.tempdir = output_folder
        self.batch_size = batch_size
        self.arate = arate
        self.font = font
        self.vrate = vrate
        self.shuffle = shuffle
        self.frate = frate
        self.codec = codec
        self.vis_type = vis_type
        self.test = test
        self.test_duration = 60 if test else None
        if isinstance(test, (int, float)) and test > 0:
            self.test_duration = test
        self.afreq = afreq
        self.processed_files = []
        self.background = background  # None = album art, path = image, hex = color
        self.to_process_files = []
        self.use_tqdm = use_tqdm and not progress_callback  # Don't use tqdm if GUI callback is provided
        
        self.is_wavecolor_generate = False if wavecolor else True
        self.wavecolor = wavecolor if wavecolor else "0xFEFEFE"
        self.wavecolor2 = wavecolor2 if wavecolor2 else "0x9400D3"
        
        self.output_folder.mkdir(exist_ok=True)
        
        # Callbacks for GUI
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # Stop flag for GUI
        self._stop_flag = False
        
        # Current ffmpeg process (for stopping)
        self._current_ffmpeg_process = None
        
        # Initialize visualization filters
        self.viz_filters = VisualizationFilters(
            vis_type=vis_type,
            frate=frate,
            afreq=afreq,
            wavecolor=self.wavecolor,
            wavecolor2=self.wavecolor2
        )
        
        # Load processed files list if exists
        self.processed_list_file = self.output_folder / "processed_files.json"
        if self.processed_list_file.exists():
            with open(self.processed_list_file, 'r', encoding='utf-8') as f:
                self.processed_files = json.load(f)
    
    def _log(self, message):
        """Send log message to callback or print."""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def _progress(self, current, total, message=""):
        """Send progress update to callback."""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def _check_stop(self):
        """Check if processing should be stopped."""
        if hasattr(self, '_stop_flag') and self._stop_flag:
            raise KeyboardInterrupt("Processing stopped by user")
    
    def stop(self):
        """Signal the converter to stop processing and kill current ffmpeg process."""
        self._stop_flag = True
        # Kill current ffmpeg process if running
        if self._current_ffmpeg_process is not None:
            try:
                self._current_ffmpeg_process.terminate()
            except:
                pass
    
    def get_mp3_files(self):
        """Get all MP3 files from input folder that haven't been processed yet."""
        all_mp3s = list(self.input_folder.glob("*.mp3"))
        if self.shuffle != 0:
            random.shuffle(all_mp3s)
        self.to_process_files = [str(f) for f in all_mp3s if str(f) not in self.processed_files]
        return self.to_process_files
    
    def get_id3_tag(self, tags, tag_name, default="Unknown"):
        """Extract ID3 tag value safely."""
        try:
            if tag_name in tags:
                value = tags[tag_name]
                if isinstance(value, list) and len(value) > 0:
                    value = value[0]
                return str(value)
        except:
            pass
        return default
    
    def find_lyrics_tag(self, tags):
        """Find standard lyrics tag (USLT)."""
        for tag in tags.keys():
            if tag.startswith("USLT"):
                value = tags[tag]
                if hasattr(value, 'text'):
                    return str(value.text)
        return None
    
    def detect_encoding(self, text):
        """Detect text encoding to handle non-English characters."""
        if isinstance(text, str):
            return text, 'utf-8'
        
        try:
            decoded = text.decode('utf-8')
            return decoded, 'utf-8'
        except (UnicodeDecodeError, AttributeError):
            try:
                result = chardet.detect(text)
                encoding = result['encoding'] or 'iso-8859-1'
                decoded = text.decode(encoding)
                return decoded, encoding
            except:
                decoded = text.decode('iso-8859-1', errors='replace')
                return decoded, 'iso-8859-1'
    
    def extract_metadata(self, mp3_path):
        """Extract metadata from MP3 file."""
        try:
            audio = MP3(mp3_path)
            tags = ID3(mp3_path)

            title = self.get_id3_tag(tags, "TIT2", Path(mp3_path).stem)
            artist = self.get_id3_tag(tags, "TPE1", "Unknown Artist")
            album_artist = self.get_id3_tag(tags, "TPE2", artist)
            album = self.get_id3_tag(tags, "TALB", "Unknown Album")
            genre = self.get_id3_tag(tags, "TCON", "")

            album_art = None
            for tag in tags.values():
                if hasattr(tag, 'mime') and tag.mime.startswith('image/'):
                    album_art = tag.data
                    break

            lyrics = self.find_lyrics_tag(tags)

            title, _ = self.detect_encoding(title)
            artist, _ = self.detect_encoding(artist)
            album_artist, _ = self.detect_encoding(album_artist)
            album, _ = self.detect_encoding(album)
            genre, _ = self.detect_encoding(genre)

            if lyrics:
                lyrics, _ = self.detect_encoding(lyrics)

            return {
                'title': title,
                'artist': artist,
                'album_artist': album_artist,
                'album': album,
                'genre': genre,
                'duration': audio.info.length,
                'album_art': album_art,
                'lyrics': lyrics,
                'path': mp3_path
            }
        except Exception as e:
            self._log(f"Error processing {mp3_path}: {e}")
            return None
    
    def create_album_art_image(self, album_art_data, output_path, size=(800, 800)):
        """Create album art image from binary data."""
        try:
            with open(output_path, 'wb') as f:
                f.write(album_art_data)

            img = Image.open(output_path)
            resized_img = img.resize((1, 1), Image.BICUBIC)
            r, g, b = resized_img.convert('RGB').getpixel((0, 0))
            if self.is_wavecolor_generate:
                self.wavecolor = f"0x{r:02x}{g:02x}{b:02x}"
            img = img.resize(size, Image.LANCZOS)
            img.save(output_path, 'JPEG', quality=95)
            return True
        except Exception as e:
            self._log(f"Error creating album art: {e}")
            return False
    
    def create_lyrics_image(self, lyrics_text, output_path, width=600, font_size=25):
        """Create a long image with lyrics that can be scrolled."""
        try:
            font = self._get_font(self.font, font_size, bold=True)
            
            paragraphs = lyrics_text.split('\n')
            lines = []
            
            for paragraph in paragraphs:
                words = paragraph.split()
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else font.getsize(test_line)
                    if hasattr(font, 'getbbox'):
                        test_width = bbox[2] - bbox[0]
                    else:
                        test_width = bbox[0]
                    
                    if test_width <= width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                lines.append('')
            
            if lines and lines[-1] == '':
                lines = lines[:-1]
            
            line_height = font_size + 5
            total_height = len(lines) * line_height + 50
            
            img = Image.new('RGBA', (width, total_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            y = 25
            for line in lines:
                if line:
                    draw.text((0, y), line, font=font, fill=(200, 200, 255, 255))
                y += line_height
            
            img.save(output_path, 'PNG')
            return total_height
        
        except Exception as e:
            self._log(f"Error creating lyrics image: {e}")
            return 0
    
    def run_ffmpeg_command(self, cmd):
        """Run FFmpeg command with proper encoding handling."""
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Store process reference for stopping
            self._current_ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='ignore',
                env=env
            )
            
            stdout, stderr = self._current_ffmpeg_process.communicate()
            
            if self._current_ffmpeg_process.returncode != 0:
                raise subprocess.CalledProcessError(self._current_ffmpeg_process.returncode, cmd, stderr=stderr)
            
            self._current_ffmpeg_process = None
            return stdout
        except KeyboardInterrupt:
            self._log("\nProcess interrupted by user. Exiting gracefully...")
            if self._current_ffmpeg_process:
                try:
                    self._current_ffmpeg_process.terminate()
                except:
                    pass
            self._current_ffmpeg_process = None
            raise
        except subprocess.CalledProcessError as e:
            self._log(f"FFmpeg command failed: {' '.join(cmd)}")
            self._log(f"FFmpeg stderr: {e.stderr}")
            self._current_ffmpeg_process = None
            raise
    
    def _get_font(self, font_path, size, bold=False):
        """Get font with optional bold weight."""
        try:
            if bold:
                bold_variants = [
                    font_path.replace('.ttf', 'b.ttf'),
                    font_path.replace('.ttf', 'Bd.ttf'),
                    font_path.replace('.ttf', 'Bold.ttf'),
                    font_path.replace('.TTF', 'B.TTF'),
                ]
                for bold_path in bold_variants:
                    if bold_path != font_path:
                        try:
                            return ImageFont.truetype(bold_path, size)
                        except:
                            pass
                try:
                    return ImageFont.truetype(font_path, size, weight='bold')
                except TypeError:
                    pass
            return ImageFont.truetype(font_path, size)
        except:
            return ImageFont.load_default()

    def _create_blurred_background(self, source_image_path, width=1920, height=1080):
        """Create blurred, scaled, and darkened background from image."""
        from PIL import ImageFilter
        
        source = Image.open(source_image_path)
        
        # Scale to fill width, maintaining aspect ratio
        source_ratio = source.width / source.height
        target_ratio = width / height
        
        if source_ratio > target_ratio:
            # Image is wider - scale to height
            new_height = height
            new_width = int(new_height * source_ratio)
        else:
            # Image is taller - scale to width
            new_width = width
            new_height = int(new_width / source_ratio)
        
        source = source.resize((new_width, new_height), Image.LANCZOS)
        
        # Crop to center
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        source = source.crop((left, top, left + width, top + height))
        
        # Apply blur
        source = source.filter(ImageFilter.GaussianBlur(radius=30))
        
        # Darken by 40%
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(source)
        source = enhancer.enhance(0.6)
        
        return source.convert('RGB')

    def _draw_text_with_outline(self, draw, position, text, font, fill, outline=None, outline_width=2):
        """Draw text with optional outline (shadow effect)."""
        x, y = position
        if outline:
            # Draw outline by drawing text at offsets around the center
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill)

    def create_background_image(self, metadata, output_path, album_art_path=None,
                                track_list_file=None, current_track_index=0):
        """Create background image with track info and track list (without lyrics)."""
        width, height = 1920, 1080
        
        # Determine background color or image
        bg_color = (0, 0, 0)
        bg_image = None
        
        if self.background:
            # Check if it's a hex color
            if self.background.startswith('#') or self.background.startswith('0x'):
                try:
                    hex_color = self.background.replace('#', '').replace('0x', '')
                    if len(hex_color) == 6:
                        bg_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                except:
                    bg_color = (0, 0, 0)
            elif Path(self.background).exists():
                # It's an image path
                bg_image = self._create_blurred_background(self.background)
        
        # If no background image or color specified, use album art as blurred background
        if bg_image is None and not self.background:
            if album_art_path and Path(album_art_path).exists():
                bg_image = self._create_blurred_background(album_art_path)
        
        # Create image
        if bg_image:
            image = bg_image.copy()
            # Add semi-transparent dark overlay for better text readability
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 80))
            image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        else:
            image = Image.new('RGB', (width, height), color=bg_color)
        
        draw = ImageDraw.Draw(image)

        try:
            try:
                title_font = self._get_font(self.font, 40, bold=True)
                info_font = self._get_font(self.font, 30, bold=True)
                list_font = self._get_font(self.font, 20)
                highlight_font = self._get_font(self.font, 24, bold=True)  # 2px larger for current track
            except:
                title_font = ImageFont.load_default()
                info_font = ImageFont.load_default()
                list_font = ImageFont.load_default()
                highlight_font = ImageFont.load_default()

            # Outline color for text
            text_outline = (55, 55, 55)  # Black outline

            if track_list_file and track_list_file.exists():
                with open(track_list_file, 'r', encoding='utf-8') as f:
                    tracks = f.readlines()

                list_x = 50
                list_y = 100
                for i, track in enumerate(tracks):
                    track_text = track.strip()
                    if i == current_track_index:
                        # Highlight current track with larger font and outline
                        self._draw_text_with_outline(draw, (list_x, list_y), track_text, 
                                                     highlight_font, fill=(255, 255, 0), 
                                                     outline=text_outline, outline_width=2)
                    else:
                        self._draw_text_with_outline(draw, (list_x, list_y), track_text,
                                                     list_font, fill=(150, 150, 150),
                                                     outline=text_outline, outline_width=1)
                    list_y += 30
            
            if album_art_path and album_art_path.exists():
                album_art = Image.open(album_art_path)
                art_size = 400
                album_art = album_art.resize((art_size, art_size), Image.LANCZOS)
                
                # Apply rounded corners mask
                radius = 20
                mask = Image.new('L', (art_size, art_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, art_size - 1, art_size - 1], radius=radius, fill=255)
                
                # Apply mask to album art
                album_art_rounded = Image.new('RGBA', (art_size, art_size), (0, 0, 0, 0))
                album_art_rounded.paste(album_art.convert('RGBA'), (0, 0), mask)
                
                # Convert main image to RGBA for compositing
                image_rgba = image.convert('RGBA')
                art_x = (width - art_size) // 2
                art_y = 80
                
                # Paste with alpha
                image_rgba.paste(album_art_rounded, (art_x, art_y), album_art_rounded)
                image = image_rgba
                draw = ImageDraw.Draw(image)  # Recreate draw for RGBA image

            title_text = metadata['title'][:50]
            artist_text = metadata['artist'][:50]
            album_text = metadata['album'][:50]
            genre_text = metadata.get('genre', '')
            
            # Calculate text positions (below album art)
            text_start_y = 520  # Below album art (80 + 400 + 40)

            # Draw title (largest, centered)
            if hasattr(draw, 'textbbox'):
                title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
            else:
                title_width = draw.textlength(title_text, font=title_font)
            title_x = (width - title_width) // 2
            self._draw_text_with_outline(draw, (title_x, text_start_y), title_text,
                                         title_font, fill=(255, 255, 255),
                                         outline=text_outline, outline_width=3)

            # Draw artist name
            if hasattr(draw, 'textbbox'):
                artist_bbox = draw.textbbox((0, 0), artist_text, font=info_font)
                artist_width = artist_bbox[2] - artist_bbox[0]
            else:
                artist_width = draw.textlength(artist_text, font=info_font)
            artist_x = (width - artist_width) // 2
            self._draw_text_with_outline(draw, (artist_x, text_start_y + 50), artist_text,
                                         info_font, fill=(255, 255, 255),
                                         outline=text_outline, outline_width=2)

            # Draw album and genre info
            info_text = f"{album_text}" if album_text else ""
            if genre_text:
                info_text += f" | {genre_text}" if info_text else f"{genre_text}"
            
            if info_text:
                if hasattr(draw, 'textbbox'):
                    info_bbox = draw.textbbox((0, 0), info_text, font=list_font)
                    info_width = info_bbox[2] - info_bbox[0]
                else:
                    info_width = draw.textlength(info_text, font=list_font)
                info_x = (width - info_width) // 2
                self._draw_text_with_outline(draw, (info_x, text_start_y + 95), info_text,
                                             list_font, fill=(180, 180, 180),
                                             outline=text_outline, outline_width=1)
            
            # Convert back to RGB for saving
            image = image.convert('RGB')
            image.save(output_path, 'JPEG', quality=95)
            return True

        except Exception as e:
            self._log(f"Error creating background image: {e}")
            image = image.convert('RGB')
            draw = ImageDraw.Draw(image)
            draw.text((100, 100), f"{metadata['title'][:30]} - {metadata['artist'][:30]}", fill=(255, 255, 255))
            image.save(output_path, 'JPEG', quality=95)
            return False
    
    def create_video_segment(self, metadata, image_path, output_path):
        """Create a video segment for a single track without lyrics."""
        self._log(f" Processing  : {metadata['title']}")
        
        duration = metadata['duration']
        if self.test_duration:
            duration = min(duration, self.test_duration)
        
        auvis_filter_part, auvis_overlay = self.viz_filters._create_audio_visualization_filter(has_lyrics=False)
        filter_complex = f"{auvis_filter_part};{auvis_overlay}"
        
        cmd = [
            'ffmpeg',
            '-filter_complex_threads', '0',
            '-stream_loop', '1', '-i', str(image_path),
            '-i', metadata['path'],
            '-filter_complex', filter_complex,
            '-map', '[outv]', '-map', '1:a',
            '-c:v', self.codec,
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-threads', '0',
            '-c:a', 'aac',
            '-ar', str(self.afreq),
            '-strict', 'experimental',
            '-threads', '0',
            '-b:a', f'{self.arate}k',
            '-b:v', f'{self.vrate}k',
            '-shortest',
            '-movflags', 'faststart',
            '-r', str(self.frate),
            str(output_path),
            '-y'
        ]
        
        try:
            self.run_ffmpeg_command(cmd)
            return True
        except Exception as e:
            self._log(f"Error creating video segment: {e}")
            return False
    
    def create_video_with_scrolling_lyrics(self, metadata, bg_image_path, lyrics_image_path,
                                           lyrics_height, output_path):
        """Create a video with scrolling lyrics."""
        self._log(f" Processing with lyrics : {metadata['title']}")
        
        duration = metadata['duration']
        if self.test_duration:
            duration = min(duration, self.test_duration)
        
        scroll_speed = (lyrics_height + 1080) / duration
        
        auvis_filter_part, auvis_overlay = self.viz_filters._create_audio_visualization_filter(has_lyrics=True)
        
        if "[0:v][auvis]overlay" in auvis_overlay:
            auvis_overlay_for_lyrics = auvis_overlay.replace("[0:v][auvis]overlay", "[lurv][auvis]overlay")
        else:
            auvis_overlay_for_lyrics = "[lurv][auvis]overlay=x=720:y=600[outv]"
        
        filter_complex = (
            f"{auvis_filter_part};"
            f"[1:v]scale=600:-1:flags=fast_bilinear,format=rgba [lyrics]; "
            f"[0:v][lyrics]overlay=x=1270:y='if(gte(t,0), (H)-{scroll_speed}*t, 0)':shortest=1,fps={str(self.frate)}[lurv];"
            f"{auvis_overlay_for_lyrics}"
        )
        
        cmd = [
            'ffmpeg',
            '-filter_complex_threads', '0',
            '-loop', '1', '-i', str(bg_image_path),
            '-loop', '1', '-i', str(lyrics_image_path),
            '-i', metadata['path'],
            '-filter_complex', filter_complex,
            '-map', '[outv]', '-map', '2:a',
            '-c:v', self.codec,
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-threads', '0',
            '-c:a', 'aac',
            '-ar', str(self.afreq),
            '-strict', 'experimental',
            '-threads', '0',
            '-b:a', f'{self.arate}k',
            '-b:v', f'{self.vrate}k',
            '-shortest',
            '-movflags', 'faststart',
            '-r', str(self.frate),
            str(output_path),
            '-y'
        ]
        
        try:
            self.run_ffmpeg_command(cmd)
            return True
        except Exception as e:
            self._log(f"Error creating video with scrolling lyrics: {e}")
            return self.create_video_segment(metadata, bg_image_path, output_path)
    
    def create_video_for_batch(self, batch_files, batch_index):
        """Create a video for a batch of MP3 files."""
        if not batch_files:
            return False
        
        metadata_list = []
        for mp3_path in batch_files:
            metadata = self.extract_metadata(mp3_path)
            if metadata:
                metadata_list.append(metadata)
        
        if not metadata_list:
            return False
        
        temp_dir_context = None
        if self.test_duration:
            temp_dir = tempfile.mkdtemp(dir=self.output_folder)
            temp_path = Path(temp_dir)
            self._log(f"Test mode: Temp directory preserved at {temp_path}")
        else:
            temp_dir_context = tempfile.TemporaryDirectory()
            temp_path = Path(temp_dir_context.name)
        
        try:
            track_list_file = temp_path / "track_list.txt"
            with open(track_list_file, 'w', encoding='utf-8') as f:
                for i, metadata in enumerate(metadata_list):
                    f.write(f"{i+1}. {metadata['title']} - {metadata['album_artist']}\n")
            
            video_segments = []
            total_tracks = len(metadata_list)
            
            # Use tqdm for CLI, plain enumerate for GUI
            if self.use_tqdm:
                track_iterator = tqdm(enumerate(metadata_list), total=total_tracks, desc=f"Batch {batch_index}", unit="track")
            else:
                track_iterator = enumerate(metadata_list)
            
            for i, metadata in track_iterator:
                self._check_stop()
                
                if not self.use_tqdm:
                    self._progress(i, total_tracks, f"Processing track: {metadata['title']}")

                self._check_stop()
                album_art_path = None
                if metadata['album_art']:
                    album_art_path = temp_path / f"album_art_{i}.jpg"
                    self.create_album_art_image(metadata['album_art'], album_art_path)

                self._check_stop()
                bg_image_path = temp_path / f"bg_{i}.jpg"
                self.create_background_image(
                    metadata, bg_image_path,
                    album_art_path if album_art_path else None,
                    track_list_file, i
                )

                self._check_stop()
                segment_path = temp_path / f"segment_{i}.mp4"

                if metadata['lyrics']:
                    lyrics_image_path = temp_path / f"lyrics_{i}.png"
                    lyrics_height = self.create_lyrics_image(metadata['lyrics'], lyrics_image_path, 600, 25)

                    if lyrics_height > 0:
                        self.create_video_with_scrolling_lyrics(
                            metadata, bg_image_path, lyrics_image_path,
                            lyrics_height, segment_path
                        )
                    else:
                        self.create_video_segment(metadata, bg_image_path, segment_path)
                else:
                    self.create_video_segment(metadata, bg_image_path, segment_path)

                video_segments.append(f"segment_{i}.mp4")
                self._log(f" File {metadata['title']} processed to segment_{i}.mp4 ")
            
            concat_file = temp_path / "concat_list.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in video_segments:
                    f.write(f"file '{segment}'\n")
            
            output_video = self.output_folder / f"batch_{batch_index}.mp4"
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                '-c', 'copy', str(output_video), '-movflags', 'faststart', '-y'
            ]
            
            self.run_ffmpeg_command(cmd)
            
            for metadata in metadata_list:
                self.processed_files.append(metadata['path'])
            
            with open(self.processed_list_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, ensure_ascii=False, indent=2)
            
            self._progress(total_tracks, total_tracks, f"Batch {batch_index} complete")
            return True
            
        except KeyboardInterrupt:
            self._log("\nProcess interrupted by user. Exiting gracefully...")
            if not self.test_duration and temp_dir_context:
                temp_dir_context.cleanup()
            raise
        except Exception as e:
            self._log(f"Error creating video: {e}")
            return False
        finally:
            if not self.test_duration and temp_dir_context:
                temp_dir_context.cleanup()
    
    def process_all(self):
        """Process all MP3 files in batches."""
        mp3_files = self.get_mp3_files()
        
        if not mp3_files:
            self._log("No MP3 files to process.")
            return
        
        total_files = len(mp3_files)
        self._log(f"Found {total_files} MP3 files to process.")
        
        try:
            for i in range(0, len(mp3_files), self.batch_size):
                batch = mp3_files[i:i + self.batch_size]
                existing_batches = len(self.processed_files) // self.batch_size
                batch_index = existing_batches
                
                self._log(f"Processing batch {batch_index} with {len(batch)} tracks...")
                
                success = self.create_video_for_batch(batch, batch_index)
                
                if success:
                    self._log(f"Successfully created video for batch {batch_index}")
                else:
                    self._log(f"Failed to create video for batch {batch_index}")
        except KeyboardInterrupt:
            self._log("\nProcess interrupted by user. Exiting gracefully...")
            raise
        
        self._log("Processing complete.")
        self._progress(total_files, total_files, "Processing complete")
