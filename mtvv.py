#!/usr/bin/env python3
"""
CLI entry point for Music To Visualized Video converter.
"""

import argparse
import subprocess
from core import MP3ToVideoConverter


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(['ffmpeg', '-version'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert MP3 files to MP4 videos with album art and lyrics'
    )
    parser.add_argument('input_folder', help='Folder containing MP3 files')
    parser.add_argument('output_folder', help='Folder to save MP4 videos')
    parser.add_argument('--batch-size', type=int, default=25,
                        help='Number of tracks per video (adequate max value is 30, default: 25)')
    parser.add_argument('--vrate', type=int, default=550,
                        help='Out video bitrate in kbits (default: 550)')
    parser.add_argument('--arate', type=int, default=192,
                        help='Audio bitrate in kbits out video (default: 192)')
    parser.add_argument('--afreq', type=int, default=44100,
                        help='Audio frequency in Hz for batch chunks (default: 44100)')
    parser.add_argument('--font', default='arial.ttf',
                        help='Font file: default = arial.ttf')
    parser.add_argument('--shuffle', type=int, default=0,
                        help='Set to 1 to shuffle input list.')
    parser.add_argument('--frate', type=int, default=30,
                        help='Video framerate (default 30).')
    parser.add_argument('--codec', default='libx264',
                        help='Codec, default - software encoding by libx264. For nvidia best - h264_nvenc.')
    parser.add_argument('--vis-type', type=int, default=0,
                        help='Visualization type: 0 for sphere showwaves (with geq), '
                             '1 for just showwaves, '
                             '2 for full-width showwaves bottom visualization, '
                             '3 for top/bottom simultaneous visualization, '
                             '4 - avectorscope, '
                             '5 - circular projection with GLSL shader. (default: 0)')
    parser.add_argument('--test', nargs='?', const=60, type=float, default=False,
                        help='Run in test mode - process only 60 seconds of each track (default). '
                             'Optionally specify duration in seconds, e.g. --test 30')
    parser.add_argument('--wavecolor',
                        help='Wave color in hex or from ffmpeg color table (default: album art dominant color)')
    parser.add_argument('--wavecolor2',
                        help='Secondary wave color in hex or from ffmpeg color table (default: 0x9400D3)')
    
    args = parser.parse_args()
    
    if not check_ffmpeg():
        print("Error: ffmpeg is required but not found. "
              "Please install ffmpeg and ensure it's in your PATH.")
        return
    
    converter = MP3ToVideoConverter(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        batch_size=args.batch_size,
        arate=args.arate,
        vrate=args.vrate,
        font=args.font,
        shuffle=args.shuffle,
        frate=args.frate,
        codec=args.codec,
        vis_type=args.vis_type,
        test=args.test,
        wavecolor=args.wavecolor,
        wavecolor2=args.wavecolor2,
        afreq=args.afreq,
        use_tqdm=True
    )
    
    try:
        converter.process_all()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully...")


if __name__ == "__main__":
    main()
