import os
import argparse
import json
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, error as ID3Error
from PIL import Image, ImageDraw, ImageFont
import subprocess
import tempfile
import chardet
import math

class MP3ToVideoConverter:
    def __init__(self, input_folder, output_folder, batch_size=25, arate=192, vrate=550, font='arial.ttf'):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        tempfile.tempdir=output_folder
        self.batch_size = batch_size
        self.arate=arate
        self.font=font
        self.vrate=vrate
        self.processed_files = []
        self.to_process_files = []
        
        # Create output folder if it doesn't exist
        self.output_folder.mkdir(exist_ok=True)
        
        # Load processed files list if exists
        self.processed_list_file = self.output_folder / "processed_files.json"
        if self.processed_list_file.exists():
            with open(self.processed_list_file, 'r') as f:
                self.processed_files = json.load(f)
    
    def get_mp3_files(self):
        """Get all MP3 files from input folder that haven't been processed yet"""
        all_mp3s = list(self.input_folder.glob("*.mp3"))
        self.to_process_files = [str(f) for f in all_mp3s if str(f) not in self.processed_files]
        return self.to_process_files
    
    def get_id3_tag(self, tags, tag_name, default="Unknown"):
        """Extract ID3 tag value safely"""
        try:
            if tag_name in tags:
                return str(tags[tag_name])
        except:
            pass
        return default
    
    def find_lyrics_tag(self, tags):
        """Find standard lyrics tag (USLT)"""
        for tag in tags.keys():
            if tag.startswith("USLT"):
                return str(tags[tag])
        return None
    
    def detect_encoding(self, text):
        """Detect text encoding to handle non-English characters"""
        if isinstance(text, str):
            return text, 'utf-8'
        
        try:
            # Try UTF-8 first
            decoded = text.decode('utf-8')
            return decoded, 'utf-8'
        except UnicodeDecodeError:
            try:
                # Try to detect encoding
                result = chardet.detect(text)
                encoding = result['encoding'] or 'iso-8859-1'
                decoded = text.decode(encoding)
                return decoded, encoding
            except:
                # Fallback to ISO-8859-1 with replacement
                decoded = text.decode('iso-8859-1', errors='replace')
                return decoded, 'iso-8859-1'
    
    def extract_metadata(self, mp3_path):
        """Extract metadata from MP3 file"""
        try:
            audio = MP3(mp3_path)
            tags = ID3(mp3_path)
            
            title = self.get_id3_tag(tags, "TIT2", Path(mp3_path).stem)
            artist = self.get_id3_tag(tags, "TPE1", "Unknown Artist")
            album_artist = self.get_id3_tag(tags, "TPE2", artist)
            album = self.get_id3_tag(tags, "TALB", "Unknown Album")
            
            # Extract album art
            album_art = None
            for tag in tags.values():
                if hasattr(tag, 'mime') and tag.mime.startswith('image/'):
                    album_art = tag.data
                    break
            
            # Find lyrics using standard ID3 tag
            lyrics = self.find_lyrics_tag(tags)
            
            # Handle encoding for text fields
            title, _ = self.detect_encoding(title)
            artist, _ = self.detect_encoding(artist)
            album_artist, _ = self.detect_encoding(album_artist)
            album, _ = self.detect_encoding(album)
            
            if lyrics:
                lyrics, _ = self.detect_encoding(lyrics)
            
            return {
                'title': title,
                'artist': artist,
                'album_artist': album_artist,
                'album': album,
                'duration': audio.info.length,
                'album_art': album_art,
                'lyrics': lyrics,
                'path': mp3_path
            }
        except Exception as e:
            print(f"Error processing {mp3_path}: {e}")
            return None
    
    def create_album_art_image(self, album_art_data, output_path, size=(800, 800)):
        """Create album art image from binary data"""
        try:
            with open(output_path, 'wb') as f:
                f.write(album_art_data)
            
            # Resize if needed
            img = Image.open(output_path)
            img = img.resize(size, Image.LANCZOS)
            img.save(output_path)
            return True
        except Exception as e:
            print(f"Error creating album art: {e}")
            return False
    
    def create_lyrics_image(self, lyrics_text, output_path, width=600, font_size=25):
        """Create a long image with lyrics that can be scrolled"""
        try:
            # Try to load a font that supports multiple languages
            try:
                font = ImageFont.truetype(self.font, font_size)
            except:
                font = ImageFont.load_default()
            
            # Split text into paragraphs while preserving existing newlines
            paragraphs = lyrics_text.split('\n')
            lines = []
            
            for paragraph in paragraphs:
                words = paragraph.split()
                current_line = []
                
                for word in words:
                    # Test if adding this word exceeds the width
                    test_line = ' '.join(current_line + [word])
                    bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else font.getsize(test_line)
                    if hasattr(font, 'getbbox'):
                        test_width = bbox[2] - bbox[0]
                    else:
                        test_width = bbox[0]
                    
                    if test_width <= width:
                        current_line.append(word)
                    else:
                        # Line is too long, start a new line
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                
                # Add the last line of the paragraph
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Add an empty line between paragraphs
                lines.append('')
            
            # Remove the last empty line if it exists
            if lines and lines[-1] == '':
                lines = lines[:-1]
            
            # Calculate total height needed
            line_height = font_size + 5
            total_height = len(lines) * line_height + 50  # Add some padding
            
            # Create image with transparent background
            img = Image.new('RGBA', (width, total_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw lyrics
            y = 25
            for line in lines:
                if line:  # Only draw non-empty lines
                    draw.text((0, y), line, font=font, fill=(200, 200, 255, 255))
                y += line_height
            
            img.save(output_path, 'PNG')
            return total_height
            
        except Exception as e:
            print(f"Error creating lyrics image: {e}")
            return 0
    
    def create_video_for_batch(self, batch_files, batch_index):
        """Create a video for a batch of MP3 files"""
        if not batch_files:
            return False
        
        # Extract metadata for all files in batch
        metadata_list = []
        for mp3_path in batch_files:
            metadata = self.extract_metadata(mp3_path)
            if metadata:
                metadata_list.append(metadata)
        
        if not metadata_list:
            return False
        
        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a text file with track list for this batch
            track_list_file = temp_path / "track_list.txt"
            with open(track_list_file, 'w', encoding='utf-8') as f:
                for i, metadata in enumerate(metadata_list):
                    f.write(f"{i+1}. {metadata['title']} - {metadata['album_artist']}\n")
            
            # Process each track in the batch
            video_segments = []
            for i, metadata in enumerate(metadata_list):
                # Create album art image if available
                album_art_path = None
                if metadata['album_art']:
                    album_art_path = temp_path / f"album_art_{i}.jpg"
                    self.create_album_art_image(metadata['album_art'], album_art_path)
                
                # Create background image with track info (without lyrics)
                bg_image_path = temp_path / f"bg_{i}.jpg"
                self.create_background_image(
                    metadata, 
                    bg_image_path, 
                    album_art_path if album_art_path else None,
                    track_list_file,
                    i  # Current track index for highlighting
                )
                
                # Create video segment for this track
                segment_path = temp_path / f"segment_{i}.mp4"
                
                # If lyrics are available, create a scrolling lyrics video
                if metadata['lyrics']:
                    lyrics_image_path = temp_path / f"lyrics_{i}.png"
                    lyrics_height = self.create_lyrics_image(metadata['lyrics'], lyrics_image_path, 600, 25)
                    
                    if lyrics_height > 0:
                        # Create video with scrolling lyrics
                        self.create_video_with_scrolling_lyrics(
                            metadata, 
                            bg_image_path, 
                            lyrics_image_path, 
                            lyrics_height,
                            segment_path
                        )
                    else:
                        # Fallback to regular video without lyrics
                        self.create_video_segment(metadata, bg_image_path, segment_path)
                else:
                    # Create regular video without lyrics
                    self.create_video_segment(metadata, bg_image_path, segment_path)
                
                video_segments.append(f"segment_{i}.mp4")
                print(f"File {metadata['title']} processed to segment_{i}.mp4 ")
            
            # Concatenate all video segments
            concat_file = temp_path / "concat_list.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in video_segments:
                    f.write(f"file '{segment}'\n")
            
            output_video = self.output_folder / f"batch_{batch_index}.mp4"
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                '-c', 'copy', str(output_video), '-y'
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Mark files as processed
                for metadata in metadata_list:
                    self.processed_files.append(metadata['path'])
                
                # Update processed files list
                with open(self.processed_list_file, 'w', encoding='utf-8') as f:
                    json.dump(self.processed_files, f)
                
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error creating video: {e}")
                return False
    
    def create_background_image(self, metadata, output_path, album_art_path=None, track_list_file=None, current_track_index=0):
        """Create background image with track info and track list (without lyrics)"""
        # Create a blank image (1920x1080)
        width, height = 1920, 1080
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to load fonts that support multiple languages
            try:
                title_font = ImageFont.truetype(self.font, 40)
                info_font = ImageFont.truetype(self.font, 30)
                list_font = ImageFont.truetype(self.font, 20)
                highlight_font = ImageFont.truetype(self.font, 22)
            except:
                # Fallback to default font
                title_font = ImageFont.load_default()
                info_font = ImageFont.load_default()
                list_font = ImageFont.load_default()
                highlight_font = ImageFont.load_default()
            
           
            
            # Add track list on the left
            if track_list_file and os.path.exists(track_list_file):
                with open(track_list_file, 'r', encoding='utf-8') as f:
                    tracks = f.readlines()
                
                list_x = 50
                list_y = 100
                for i, track in enumerate(tracks):
                    if i == current_track_index:
                        # Highlight the current track
                        draw.text((list_x, list_y), track.strip(), font=highlight_font, fill=(255, 255, 0))
                    else:
                        draw.text((list_x, list_y), track.strip(), font=list_font, fill=(150, 150, 150))
                    list_y += 30
            
             # Add album art if available
            if album_art_path and os.path.exists(album_art_path):
                album_art = Image.open(album_art_path)
                art_size = 400
                album_art = album_art.resize((art_size, art_size), Image.LANCZOS)
                art_x = (width - art_size) // 2
                art_y = 100
                image.paste(album_art, (art_x, art_y))
            
            # Add track info below album art
            title_text = metadata['title']
            artist_text = f"{metadata['album_artist']} - {metadata['album']}"
            
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            title_y = 550 if album_art_path else 100
            
            draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255))
            
            artist_bbox = draw.textbbox((0, 0), artist_text, font=info_font)
            artist_width = artist_bbox[2] - artist_bbox[0]
            artist_x = (width - artist_width) // 2
            artist_y = title_y + 50
            
            draw.text((artist_x, artist_y), artist_text, font=info_font, fill=(200, 200, 200))
            # Save the image
            image.save(output_path)
            return True
            
        except Exception as e:
            print(f"Error creating background image: {e}")
            # Fallback: save a simple image
            draw.text((100, 100), f"{metadata['title']} - {metadata['album_artist']}", fill=(255, 255, 255))
            image.save(output_path)
            return False
    
    def create_video_segment(self, metadata, image_path, output_path):
        """Create a video segment for a single track without lyrics"""
        duration = metadata['duration']
        filter_complex = (
            f"aformat=channel_layouts=mono,showwaves=mode=cline:s=480X480:colors=Violet[auvis];"
            f"[0:v][auvis]overlay=x=720:y=600[outv]"
        )
        cmd = [
            'ffmpeg', '-loop', '1', '-i', str(image_path), '-i', metadata['path'],
            '-filter_complex', filter_complex,'-map', '[outv]', '-map', '1:a',
            '-c:v', 'libx264','-preset','veryfast',  '-t', str(duration), '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-strict', 'experimental', '-b:a', str(self.arate)+'k','-b:v', str(self.vrate)+'k',
            '-shortest', str(output_path), '-y'
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating video segment: {e}")
            return False
    
    def create_video_with_scrolling_lyrics(self, metadata, bg_image_path, lyrics_image_path, lyrics_height, output_path):
        """Create a video with scrolling lyrics"""
        duration = metadata['duration']
        
        # Calculate scroll speed (pixels per second)
        # We want the lyrics to scroll from bottom to top during the song duration
        scroll_speed = (lyrics_height + 1080) / duration  # Add video height to ensure full scroll
        
        # Create a complex filter for scrolling lyrics
        filter_complex = (
            f"[1:v]scale=600:-1,format=rgba [lyrics]; "
            f"aformat=channel_layouts=mono,showwaves=mode=cline:s=480X480:colors=Violet[auvis];"
            f"[0:v][lyrics]overlay=x=1270:y='if(gte(t,0), (H)-{scroll_speed}*t, 0)':shortest=1[lurv];"
            f"[lurv][auvis]overlay=x=720:y=600[outv]"
        )
        
        cmd = [
            'ffmpeg', '-loop', '1', '-i', str(bg_image_path),
            '-loop', '1', '-i', str(lyrics_image_path),
            '-i', metadata['path'],
            '-filter_complex', filter_complex,
            '-map', '[outv]', '-map', '2:a',
            '-c:v', 'libx264','-preset','veryfast', '-t', str(duration), '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-strict', 'experimental', '-b:a', str(self.arate)+'k','-b:v', str(self.vrate)+'k',
            '-shortest', str(output_path), '-y'
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating video with scrolling lyrics: {e}")
            # Fallback to regular video without lyrics
            return self.create_video_segment(metadata, bg_image_path, output_path)
    
    def process_all(self):
        """Process all MP3 files in batches"""
        mp3_files = self.get_mp3_files()
        
        if not mp3_files:
            print("No MP3 files to process.")
            return
        
        print(f"Found {len(mp3_files)} MP3 files to process.")
        
        # Process in batches
        for i in range(0, len(mp3_files), self.batch_size):
            batch = mp3_files[i:i + self.batch_size]
            batch_index = i // self.batch_size + 1
            
            print(f"Processing batch {batch_index} with {len(batch)} tracks...")
            
            success = self.create_video_for_batch(batch, batch_index)
            
            if success:
                print(f"Successfully created video for batch {batch_index}")
            else:
                print(f"Failed to create video for batch {batch_index}")
        
        print("Processing complete.")

def main():
    parser = argparse.ArgumentParser(description='Convert MP3 files to MP4 videos with album art and lyrics')
    parser.add_argument('input_folder', help='Folder containing MP3 files')
    parser.add_argument('output_folder', help='Folder to save MP4 videos')
    parser.add_argument('--batch-size', type=int, default=25, help='Number of tracks per video (adequate max value is 30, default: 25)')
    parser.add_argument('--vrate', type=int, default=550, help='Out video bitrate in kbits (default: 550)')
    parser.add_argument('--arate', type=int, default=192, help='Audio bitrate in kbits out video (default: 192)')
    parser.add_argument('--font', default='arial.ttf', help='Font file: default = arial.ttf')
    args = parser.parse_args()
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is required but not found. Please install ffmpeg and ensure it's in your PATH.")
        return
    
    # Process the files
    converter = MP3ToVideoConverter(args.input_folder, args.output_folder, args.batch_size, args.arate, args.vrate, args.font)
    converter.process_all()

if __name__ == "__main__":
    main()
