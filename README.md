# MusicToVisualizedVideo
Batch converts folder of mp3 music files and creates output video with album cover , lyrics<br>
( only if original file have it ) and audio visualization. Uses python 3.12 and FFMpeg.<br>
<img width="2613" height="1321" alt="image" src="https://github.com/user-attachments/assets/321b625e-1391-4a72-896b-cef89aabf62c" />

# How to use:
Download project (as zip or clone)<br>
Install python 3.12 (or use portable if you like) <br>
Download ffmpeg https://www.ffmpeg.org/download.html <br>
add ffmpeg folder to os path or just drop ffprobe and ffmpeg files inside script folder<br>
then<br>

      pip install -r  requirements.txt
      
(or use venv if you like it, i am to lazy to describe)<br>

```
python.exe mtvv.py  ./ ./out

or if you using nvidia and downloaded some font and placed inside folder (mine most used variant)

python mtvv.py ./ ./out --batch-size 30  --vrate 1550 --arate 128 --font NotoSerifJP-VariableFont_wght.ttf --frate 60 --codec h264_nvenc

```

<br>
Where - ./ is input folder and ./out is output folder (for a sample we assume you placed script directly to music folder).<br><br>

```
usage: mtvv.py [-h] [--batch-size BATCH_SIZE] [--vrate VRATE] [--arate ARATE] [--font FONT] [--shuffle SHUFFLE]
               [--frate FRATE] [--codec CODEC] [--vis-type VIS_TYPE] [--test] [--wavecolor WAVECOLOR]
               [--wavecolor2 WAVECOLOR2]
               input_folder output_folder

positional arguments:
  input_folder          Folder containing MP3 files
  output_folder         Folder to save MP4 videos

options:
  -h, --help            show this help message and exit
  --batch-size BATCH_SIZE
                        Number of tracks per video (adequate max value is 30, default: 25)
  --vrate VRATE         Out video bitrate in kbits (default: 550)
  --arate ARATE         Audio bitrate in kbits out video (default: 192)
  --font FONT           Font file: default = arial.ttf
  --shuffle SHUFFLE     Set to 1 to shuffle input list.
  --frate FRATE         Video framerate (default 30).
  --codec CODEC         Codec, default - software encoding by libx264.For nvidia best - h264_nvenc.
  --vis-type VIS_TYPE   Visualization type: 0 for sphere showwaves (with geq), 1 for just showwaves, 2 for full-width
                        showwaves bottom visualization, 3 for top/bottom simultaneous visualization, 4 - avectorscope.
                        (default: 0)
  --test                Run in test mode - process only 60 seconds of each track
  --wavecolor WAVECOLOR
                        Wave color in hex or from ffmpeg color table (default: album art dominant color)
  --wavecolor2 WAVECOLOR2
                        Secondary wave color in hex or from ffmpeg color table (default: 0x9400D3)
```
  
# How it works:

Its grabs files from input folder, create output folder with temp inside. <br>
Next its analyze first input batch of files and extract metadata with album cover and lyrics.<br>
Lyrics converted to long transparent image thats will be added to chunk segment output temp video file (you can check it then its fully process first file in first batch).<br>
Then ffmpeg combines all of it and add audio visualisation to segment and proceed next mp3 file.<br>
After all files in batch is processed, scripts calls ffmpeg to concat segments to final batch output, write it to processed_files.json and iterate to next batch of files.<br>
If you stop it after batch, on a next launch with same output folder, it will check for processed_files.json and ignore already batched files.<br>
To stop it doing that, just remove processed_files.json.<br>
