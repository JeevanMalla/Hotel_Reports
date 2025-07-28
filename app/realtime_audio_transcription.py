import streamlit as st
import json

def st_realtime_audio():
    """
    Creates a real-time audio transcription component using OpenAI's Realtime API.
    Returns the transcribed text.
    """
    # Get OpenAI API key from Streamlit secrets
    api_key = st.secrets.get("openai", {}).get("api_key", "")
    
    if not api_key:
        st.error("OpenAI API key not found in Streamlit secrets.")
        return None
    
    # JavaScript code for real-time audio transcription
    st_realtime_js = f"""
    const realtimeAudio = () => {{
        let socket;
        let mediaRecorder;
        let audioStream;
        let isRecording = false;
        let transcription = "";
        
        const apiKey = "{api_key}";
        
        const startRecording = async () => {{
            try {{
                // Get audio stream
                audioStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                
                // Create WebSocket connection to OpenAI's Realtime API
                socket = new WebSocket('wss://api.openai.com/v1/realtime?intent=transcription');
                
                socket.onopen = () => {{
                    // Send authentication message
                    socket.send(JSON.stringify({{
                        type: 'auth',
                        token: apiKey
                    }}));
                    
                    // Configure transcription
                    socket.send(JSON.stringify({{
                        type: 'config',
                        language: 'en',
                        model: 'whisper-1'
                    }}));
                    
                    // Start recording
                    mediaRecorder = new MediaRecorder(audioStream);
                    
                    mediaRecorder.ondataavailable = (event) => {{
                        if (event.data.size > 0 && socket && socket.readyState === WebSocket.OPEN) {{
                            // Convert audio data to binary and send to WebSocket
                            event.data.arrayBuffer().then(buffer => {{
                                socket.send(JSON.stringify({{
                                    type: 'audio',
                                    data: Array.from(new Uint8Array(buffer))
                                }}));
                            }});
                        }}
                    }};
                    
                    mediaRecorder.start(100); // Collect 100ms of audio at a time
                    isRecording = true;
                    document.getElementById('status').textContent = 'Recording... Speak now';
                    document.getElementById('start-button').disabled = true;
                    document.getElementById('stop-button').disabled = false;
                }};
                
                socket.onmessage = (event) => {{
                    const message = JSON.parse(event.data);
                    if (message.type === 'transcription') {{
                        transcription = message.text;
                        document.getElementById('transcription').textContent = transcription;
                    }}
                }};
                
                socket.onerror = (error) => {{
                    console.error('WebSocket Error:', error);
                    document.getElementById('status').textContent = 'Error: ' + error.message;
                }};
                
                socket.onclose = () => {{
                    console.log('WebSocket connection closed');
                }};
                
            }} catch (error) {{
                console.error('Error starting recording:', error);
                document.getElementById('status').textContent = 'Error: ' + error.message;
            }}
        }};
        
        const stopRecording = () => {{
            if (mediaRecorder && isRecording) {{
                mediaRecorder.stop();
                isRecording = false;
            }}
            
            if (audioStream) {{
                audioStream.getTracks().forEach(track => track.stop());
            }}
            
            if (socket && socket.readyState === WebSocket.OPEN) {{
                socket.send(JSON.stringify({{ type: 'end' }}));
                // Don't close the socket yet to receive final transcription
                setTimeout(() => {{
                    socket.close();
                    Streamlit.setComponentValue(transcription);
                    document.getElementById('status').textContent = 'Recording stopped';
                    document.getElementById('start-button').disabled = false;
                    document.getElementById('stop-button').disabled = true;
                }}, 1000);
            }}
        }};
        
        // Set up event listeners
        document.getElementById('start-button').addEventListener('click', startRecording);
        document.getElementById('stop-button').addEventListener('click', stopRecording);
    }};
    
    // Initialize the component
    realtimeAudio();
    """
    
    # HTML for the component
    st_realtime_html = """
    <div style="display: flex; flex-direction: column; align-items: center; padding: 10px;">
        <div style="margin-bottom: 10px;">
            <button id="start-button" style="background-color: #FF4B4B; color: white; border: none; border-radius: 4px; padding: 8px 16px; margin-right: 10px;">Start Recording</button>
            <button id="stop-button" disabled style="background-color: #4B4BFF; color: white; border: none; border-radius: 4px; padding: 8px 16px;">Stop Recording</button>
        </div>
        <p id="status">Ready to record</p>
        <div style="margin-top: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; width: 100%; min-height: 60px;">
            <p><strong>Real-time Transcription:</strong></p>
            <p id="transcription" style="font-style: italic;"></p>
        </div>
    </div>
    """
    
    # Combine HTML and JavaScript
    components_html = f"{st_realtime_html}<script>{st_realtime_js}</script>"
    
    # Use the Streamlit component
    transcription = st.components.v1.html(components_html, height=250)
    
    return transcription
