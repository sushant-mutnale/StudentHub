"""
Voice Interview Demo Page Route
Test the voice interview functionality
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/voice-interview", response_class=HTMLResponse)
async def voice_interview_demo():
    """Simple demo page for voice interview testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Interview Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .demo-container {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            .info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover {
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="demo-container">
            <h1>🎤 Voice Interview Demo</h1>
            
            <div class="info">
                <h3>How it works:</h3>
                <ol>
                    <li>Click "Start Voice Interview" in the frontend app</li>
                    <li>Interviewer videos will play (asking.mp4 & listening.mp4)</li>
                    <li>Speak your answer when prompted</li>
                    <li>AI transcribes, evaluates, and asks next question</li>
                </ol>
                
                <h3>Videos loaded:</h3>
                <ul>
                    <li>✅ <code>/interviewer/asking.mp4</code> - Asking state</li>
                    <li>✅ <code>/interviewer/listening.mp4</code> - Listening state</li>
                </ul>
                
                <h3>Backend Services:</h3>
                <ul>
                    <li>✅ STT Service (Faster-Whisper)</li>
                    <li>✅ TTS Service (Piper)</li>
                    <li>✅ Voice Routes (/api/voice/*)</li>
                </ul>
            </div>
            
            <a href="/" class="btn">Go to App</a>
        </div>
    </body>
    </html>
    """
