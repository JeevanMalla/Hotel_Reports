import streamlit as st
import tempfile
import os
import numpy as np
import queue
import threading
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

# RTC Configuration for WebRTC (using Google's STUN server)
rtc_configuration = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

def save_audio_frames(frames, output_path):
    """
    Save audio frames to a WAV file
    
    Args:
        frames: List of audio frames
        output_path: Path to save the WAV file
    """
    import wave
    import struct
    
    # Concatenate all audio frames
    audio_data = b''.join(frames)
    
    # Convert to WAV format
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(16000)  # 16kHz sample rate
        wav_file.writeframes(audio_data)

def create_audio_recorder():
    """
    Create a live audio recorder using streamlit-webrtc
    
    Returns:
        Tuple of (webrtc_ctx, audio_path) where audio_path is the path to the recorded audio file
    """
    # Create a temporary file to store the audio
    audio_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        audio_path = tmp_file.name
    
    # Create a queue to store audio frames
    audio_frames = []
    lock = threading.Lock()
    
    # Define callback for audio frames
    def audio_frame_callback(frame):
        with lock:
            # Get audio samples from the frame
            sound = frame.to_ndarray()
            # Convert to bytes
            sound_bytes = sound.tobytes()
            # Add to frames list
            audio_frames.append(sound_bytes)
        
        # Return the frame unchanged
        return frame
    
    # Create the WebRTC streamer
    webrtc_ctx = webrtc_streamer(
        key="audio-recorder",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=rtc_configuration,
        audio_frame_callback=audio_frame_callback,
        video_frame_callback=None,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    # Add a button to stop recording and process the audio
    if webrtc_ctx.state.playing and st.button("Stop Recording and Process"):
        webrtc_ctx.video_transformer.close()
        with lock:
            if audio_frames:
                # Save audio frames to file
                save_audio_frames(audio_frames, audio_path)
                return webrtc_ctx, audio_path
    
    return webrtc_ctx, audio_path
