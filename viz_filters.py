"""
Visualization filters for Music To Visualized Video converter.
Contains audio visualization filter generation and video creation with visualizations.
"""


class VisualizationFilters:
    """Handles audio visualization filter creation and video segment generation."""
    
    def __init__(self, vis_type=0, frate=30, afreq=44100, wavecolor="0xFEFEFE", wavecolor2="0x9400D3"):
        """
        Initialize visualization filters.
        
        Args:
            vis_type: Visualization type (0-5)
            frate: Video framerate
            afreq: Audio frequency in Hz
            wavecolor: Primary wave color in hex
            wavecolor2: Secondary wave color in hex
        """
        self.vis_type = vis_type
        self.frate = frate
        self.afreq = afreq
        self.wavecolor = wavecolor
        self.wavecolor2 = wavecolor2

    def _create_audio_visualization_filter(self, has_lyrics=False):
        """Create and return the audio visualization filter complex and overlay string.

        Args:
            has_lyrics: Whether lyrics are being used (affects audio stream index)

        Returns a tuple: (filter_complex_part, overlay_expression)
        where filter_complex_part produces [auvis] and overlay_expression is the overlay
        placement string to be appended in the overall filter_complex.
        """
        # Audio stream index depends on whether lyrics are used
        audio_index = 2 if has_lyrics else 1

        # Dictionary mapping visualization types to their filter configurations
        vis_configs = {

            1: (
                # Alternative visualization without geq
                (
                    f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                    f"showwaves=mode=cline:draw=full:s=240x240:colors={self.wavecolor2}|{self.wavecolor}:rate={str(self.frate)},"
                    f"scale=480:480:flags=fast_bilinear[auvis]"
                ),
                "[0:v][auvis]overlay=x=720:y=600[outv]"
            ),
            2: (
                # Full-width bottom visualization (10% height)
                (
                    f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                    f"showwaves=mode=cline:draw=full:s=720x108:colors={self.wavecolor2}|{self.wavecolor}:rate={str(self.frate)},"
                    f"format=rgba,colorchannelmixer=aa=0.85,scale=1920:432:flags=fast_bilinear[auvis]"
                ),
                "[0:v][auvis]overlay=x=0:y=864[outv]"
            ),
            3: (
                # Top / bottom simultaneous visualization
                (
                    f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                    f"showwaves=mode=cline:draw=full:s=720x108:colors={self.wavecolor}:rate={str(self.frate)},"
                    f"split[wave1][wave2];"
                    f"[wave1]crop=720:54:0:54[wave1_cropped];"
                    f"[wave2]crop=720:54:0:0[wave2_cropped];"
                    f"[wave1_cropped]pad=720:216:0:0:color=0x00000000[wave1_padded];"
                    f"[wave2_cropped]pad=720:216:0:162:color=0x00000000[wave2_padded];"
                    f"[wave1_padded][wave2_padded]vstack[temp_screen];"
                    f"[temp_screen]format=rgba,colorchannelmixer=aa=0.85,scale=1920:1080:flags=fast_bilinear[auvis]"
                ),
                "[0:v][auvis]overlay=x=0:y=0[outv]"
            ),
            4: (
                # Alternative visualization using avectorscope
                (
                    f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                    f"avectorscope=mode=lissajous:swap=1:draw=line:s=720x720:rate={str(self.frate)},"
                    f"rotate=90*PI/180:oh=ow[auvis]"
                ),
                "[0:v][auvis]overlay=x=600:y=440[outv]"
            ),
            5: (
                # Circular projection visualization using GLSL shader
                (
                    f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                    f"showwaves=mode=cline:draw=full:s=120x120:colors={self.wavecolor2}|{self.wavecolor}:split_channels=1:rate={str(self.frate)},"
                    f"scale=480:480:flags=fast_bilinear[wave],"
                    f"[wave]libplacebo=custom_shader_path=circle.glsl[auvis]"
                ),
                "[0:v][auvis]overlay=x=720:y=600[outv]"
            ),
        }

        # Default configuration (vis_type 0) - Original visualization with geq
        default_config = (
            (
                f"[{audio_index}:a]aformat=sample_fmts=fltp:sample_rates={self.afreq}:channel_layouts=stereo,"
                f"showwaves=mode=cline:draw=full:s=240x240:colors={self.wavecolor2}|{self.wavecolor}:split_channels=1:rate={str(self.frate)},"
                f"geq='p(mod(W/PI*(PI+atan2(H/2-Y,X-W/2)),W), H-2*hypot(H/2-Y,X-W/2))':"
                f"a='alpha(mod(W/PI*(PI+atan2(H/2-Y,X-W/2)),W), H-2*hypot(H/2-Y,X-W/2))',scale=480:480:flags=fast_bilinear[auvis]"
            ),
            "[0:v][auvis]overlay=x=720:y=600[outv]"
        )

        # Switch-case using dictionary get method
        return vis_configs.get(self.vis_type, default_config)
