#!/usr/bin/env python3
"""
Nova Sonic Sales Training - App Runner Compatible Version
Uses standard boto3 for better compatibility
"""

import os
import json
import logging
import base64
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nova-sonic-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# HTML template for the interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Nova Sonic Sales Training</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .status { padding: 15px; margin: 15px 0; border-radius: 8px; font-weight: 500; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        .control-group { background: #f8f9fa; padding: 20px; border-radius: 8px; }
        select, button { padding: 12px; margin: 10px 5px; border-radius: 6px; font-size: 16px; }
        button { background: #007bff; color: white; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        button:disabled { background: #6c757d; cursor: not-allowed; }
        .btn-success { background: #28a745; }
        .btn-danger { background: #dc3545; }
        .mic-section { text-align: center; padding: 30px; background: #f8f9fa; border-radius: 12px; margin: 20px 0; }
        .mic-button { width: 100px; height: 100px; border-radius: 50%; font-size: 2.5rem; border: none; cursor: pointer; margin: 20px; }
        .mic-ready { background: #28a745; }
        .mic-recording { background: #dc3545; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
        .conversation { background: #f8f9fa; border-radius: 8px; padding: 20px; min-height: 300px; max-height: 400px; overflow-y: auto; margin: 20px 0; }
        .message { margin: 15px 0; padding: 12px; border-radius: 8px; max-width: 80%; }
        .message.user { background: #007bff; color: white; margin-left: auto; text-align: right; }
        .message.assistant { background: #e9ecef; color: #495057; margin-right: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Nova Sonic Sales Training</h1>
            <p>Advanced AI-Powered Sales Practice</p>
        </div>

        <div id="status" class="status info">Connecting to service...</div>

        <div class="controls">
            <div class="control-group">
                <h3>🎯 Training Scenario</h3>
                <select id="scenarioSelect">
                    <option value="">Choose scenario...</option>
                    <option value="vmware-migration">VMware Migration</option>
                    <option value="situational-fluency">Situational Fluency</option>
                    <option value="smb-prospecting">SMB Prospecting</option>
                </select>
            </div>
            <div class="control-group">
                <h3>🔊 AI Voice</h3>
                <select id="voiceSelect">
                    <option value="Joanna">Joanna (US Female)</option>
                    <option value="Matthew">Matthew (US Male)</option>
                    <option value="Amy">Amy (UK Female)</option>
                </select>
            </div>
        </div>

        <div style="text-align: center;">
            <button id="startBtn" class="btn-success">🚀 Start Training Session</button>
            <button id="endBtn" class="btn-danger" disabled style="display: none;">⏹️ End Session</button>
            <button id="testBtn">🧪 Test Connection</button>
        </div>

        <div class="mic-section">
            <div id="micStatus">Click microphone to speak</div>
            <button id="micButton" class="mic-button mic-ready" disabled>🎤</button>
        </div>

        <div class="conversation" id="conversation">
            <div style="text-align: center; color: #666; padding: 40px;">
                <h3>Ready for Sales Training</h3>
                <p>Select a scenario and start your session to begin.</p>
            </div>
        </div>

        <div id="messages"></div>
    </div>

    <script>
        const socket = io();
        let currentSession = null;
        let isRecording = false;
        let mediaRecorder = null;

        // Socket events
        socket.on('connect', function() {
            updateStatus('✅ Connected to Nova Sonic service', 'success');
        });

        socket.on('disconnect', function() {
            updateStatus('❌ Disconnected from service', 'error');
        });

        socket.on('session_started', function(data) {
            currentSession = data.session_id;
            updateStatus('🎯 Training session active', 'success');
            toggleControls(true);
            addMessage('Session started! AI customer is ready.', 'system');
        });

        socket.on('session_ended', function(data) {
            currentSession = null;
            updateStatus('Session ended', 'info');
            toggleControls(false);
            addMessage('Training session completed.', 'system');
        });

        socket.on('ai_response', function(data) {
            addMessage(data.text, 'assistant');
            if (data.audio) {
                playAudio(data.audio);
            }
        });

        socket.on('test_result', function(data) {
            addMessage('🧪 Test Result: ' + JSON.stringify(data, null, 2), 'system');
        });

        socket.on('error', function(data) {
            updateStatus('❌ Error: ' + data.message, 'error');
        });

        // UI functions
        function updateStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }

        function addMessage(content, role) {
            const conversation = document.getElementById('conversation');
            
            // Clear placeholder
            const placeholder = conversation.querySelector('div[style*="text-align: center"]');
            if (placeholder) placeholder.remove();

            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + role;
            messageDiv.innerHTML = content + '<div style="font-size: 11px; opacity: 0.7; margin-top: 5px;">' + new Date().toLocaleTimeString() + '</div>';
            
            conversation.appendChild(messageDiv);
            conversation.scrollTop = conversation.scrollHeight;
        }

        function toggleControls(sessionActive) {
            const startBtn = document.getElementById('startBtn');
            const endBtn = document.getElementById('endBtn');
            const micButton = document.getElementById('micButton');

            if (sessionActive) {
                startBtn.style.display = 'none';
                endBtn.style.display = 'inline-block';
                endBtn.disabled = false;
                micButton.disabled = false;
            } else {
                startBtn.style.display = 'inline-block';
                endBtn.style.display = 'none';
                startBtn.disabled = false;
                micButton.disabled = true;
            }
        }

        async function playAudio(audioBase64) {
            try {
                const audioBytes = atob(audioBase64);
                const audioArray = new Uint8Array(audioBytes.length);
                for (let i = 0; i < audioBytes.length; i++) {
                    audioArray[i] = audioBytes.charCodeAt(i);
                }
                const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                await audio.play();
                URL.revokeObjectURL(audioUrl);
            } catch (error) {
                console.error('Failed to play audio:', error);
            }
        }

        // Event handlers
        document.getElementById('startBtn').onclick = function() {
            const scenario = document.getElementById('scenarioSelect').value;
            const voice = document.getElementById('voiceSelect').value;
            
            if (!scenario) {
                alert('Please select a scenario');
                return;
            }
            
            socket.emit('start_session', { scenario: scenario, voice: voice });
        };

        document.getElementById('endBtn').onclick = function() {
            if (currentSession) {
                socket.emit('end_session', { session_id: currentSession });
            }
        };

        document.getElementById('testBtn').onclick = function() {
            socket.emit('test_connection');
        };

        document.getElementById('micButton').onclick = function() {
            if (!currentSession) {
                alert('Please start a session first');
                return;
            }
            // Microphone functionality would be implemented here
            addMessage('Microphone clicked - voice input would be processed here', 'user');
        };
    </script>
</body>
</html>
'''

class SalesTrainingSession:
    """Manages a sales training session using standard boto3"""
    
    def __init__(self, session_id, scenario='vmware-migration', voice='Joanna'):
        self.session_id = session_id
        self.scenario = scenario
        self.voice = voice
        self.conversation_history = []
        
        # Initialize AWS clients
        try:
            self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            self.polly = boto3.client('polly', region_name='us-east-1')
            logger.info(f"AWS clients initialized for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            self.bedrock = None
            self.polly = None

    def get_scenario_prompt(self):
        """Get scenario-specific prompts"""
        prompts = {
            'vmware-migration': "You are an IT manager evaluating AWS for VMware migration. You have concerns about cost and complexity. Ask specific technical questions and express realistic concerns about the migration process. Keep responses conversational, 2-3 sentences.",
            'situational-fluency': "You are a technical decision maker considering cloud adoption. You have concerns about security, compliance, and vendor lock-in. Challenge the salesperson with thoughtful questions. Keep responses conversational, 2-3 sentences.",
            'smb-prospecting': "You are a small business owner interested in cloud solutions but cost-conscious. You need simple explanations and reassurance about costs and complexity. Keep responses practical, 2-3 sentences."
        }
        return prompts.get(self.scenario, prompts['situational-fluency'])

    async def get_ai_response(self, user_message):
        """Generate AI response using standard Bedrock"""
        try:
            if not self.bedrock:
                return "I'm sorry, I'm having trouble connecting to the AI service right now."
            
            # Build prompt with scenario context
            system_prompt = self.get_scenario_prompt()
            
            # Build conversation context
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self.conversation_history[-4:]  # Last 4 messages
            ])
            
            full_prompt = f"{system_prompt}\n\nConversation:\n{context}\n\nUser: {user_message}\n\nAssistant:"
            
            # Call Bedrock Claude
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 300,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": full_prompt}]
                })
            )
            
            response_body = json.loads(response['body'].read())
            ai_response = response_body['content'][0]['text'].strip()
            
            # Update conversation history
            self.conversation_history.extend([
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': ai_response}
            ])
            
            logger.info(f"Generated AI response for session {self.session_id}")
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            return self.get_fallback_response()

    def get_fallback_response(self):
        """Fallback responses when AI fails"""
        responses = {
            'vmware-migration': "That's interesting. Can you tell me more about how this would work with our current VMware environment?",
            'situational-fluency': "I appreciate that information. What would you say are the main benefits compared to our current setup?",
            'smb-prospecting': "That sounds helpful. Can you explain how this would work for a business our size?"
        }
        return responses.get(self.scenario, "That's a good point. Can you elaborate on that?")

    async def synthesize_speech(self, text):
        """Convert text to speech using Polly"""
        try:
            if not self.polly:
                return None
            
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=self.voice,
                Engine='neural'
            )
            
            audio_data = response['AudioStream'].read()
            return base64.b64encode(audio_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            return None

# Global session manager
active_sessions = {}

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Nova Sonic Sales Training',
        'active_sessions': len(active_sessions),
        'aws_region': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
        'has_aws_credentials': bool(os.environ.get('AWS_ACCESS_KEY_ID')),
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    emit('connected', {'status': 'Connected to Nova Sonic service'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")

@socketio.on('test_connection')
def handle_test():
    """Test connection and AWS services"""
    logger.info("Testing connection and AWS services")
    
    test_result = {
        'app_runner_working': True,
        'aws_credentials': bool(os.environ.get('AWS_ACCESS_KEY_ID')),
        'aws_region': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
        'timestamp': datetime.now().isoformat()
    }
    
    # Test AWS connection
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            test_result['aws_connection'] = True
            
            # Test Bedrock
            try:
                bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
                test_result['bedrock_available'] = True
            except Exception as e:
                test_result['bedrock_available'] = False
                test_result['bedrock_error'] = str(e)
            
            # Test Polly
            try:
                polly = boto3.client('polly', region_name='us-east-1')
                test_result['polly_available'] = True
            except Exception as e:
                test_result['polly_available'] = False
                test_result['polly_error'] = str(e)
        else:
            test_result['aws_connection'] = False
    except Exception as e:
        test_result['aws_connection'] = False
        test_result['aws_error'] = str(e)
    
    emit('test_result', test_result)

@socketio.on('start_session')
def handle_start_session(data):
    """Start a new training session"""
    try:
        scenario = data.get('scenario', 'vmware-migration')
        voice = data.get('voice', 'Joanna')
        session_id = f"session_{int(datetime.now().timestamp())}"
        
        logger.info(f"Starting session {session_id} - Scenario: {scenario}, Voice: {voice}")
        
        # Create session
        session = SalesTrainingSession(session_id, scenario, voice)
        active_sessions[session_id] = session
        
        emit('session_started', {
            'session_id': session_id,
            'scenario': scenario,
            'voice': voice
        })
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        emit('error', {'message': f'Failed to start session: {str(e)}'})

@socketio.on('end_session')
def handle_end_session(data):
    """End training session"""
    try:
        session_id = data.get('session_id')
        if session_id in active_sessions:
            del active_sessions[session_id]
            logger.info(f"Ended session {session_id}")
        
        emit('session_ended', {'session_id': session_id})
        
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        emit('error', {'message': f'Failed to end session: {str(e)}'})

if __name__ == '__main__':
    logger.info("Starting Nova Sonic Sales Training App Runner service...")
    
    # Check AWS credentials
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        logger.warning("AWS credentials not found in environment variables")
    else:
        logger.info("AWS credentials found")
    
    # Get port from environment
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting on port {port}")
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
