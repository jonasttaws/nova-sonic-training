#!/usr/bin/env python3
"""
Nova Sonic Sales Training - App Runner Web Application
Provides web interface for Nova Sonic bidirectional streaming
"""

import os
import asyncio
import base64
import json
import uuid
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import queue
import time

# AWS SDK imports
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nova-sonic-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class NovaSonicSession:
    """Manages a Nova Sonic streaming session"""
    
    def __init__(self, session_id, scenario='vmware-migration', voice_id='matthew'):
        self.session_id = session_id
        self.scenario = scenario
        self.voice_id = voice_id
        self.model_id = 'amazon.nova-sonic-v1:0'
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Nova Sonic components
        self.client = None
        self.stream = None
        self.response_task = None
        self.is_active = False
        
        # Unique IDs for Nova Sonic protocol
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        
        # Audio queues
        self.audio_output_queue = queue.Queue()
        self.audio_input_queue = queue.Queue()
        
        # Session state
        self.role = None
        self.display_assistant_text = False
        
        logger.info(f"Created Nova Sonic session: {session_id}")

    def _initialize_client(self):
        """Initialize the Bedrock client"""
        try:
            config = Config(
                endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
                region=self.region,
                aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
                http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
                http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
            )
            self.client = BedrockRuntimeClient(config=config)
            logger.info("Nova Sonic client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            raise

    async def send_event(self, event_json):
        """Send an event to the Nova Sonic stream"""
        try:
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
            )
            await self.stream.input_stream.send(event)
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            raise

    def get_scenario_prompt(self):
        """Get sales training scenario prompts"""
        prompts = {
            'vmware-migration': """You are an experienced IT infrastructure manager at a mid-size company currently running VMware vSphere. You're evaluating AWS for potential migration but have realistic concerns about cost, complexity, downtime, and staff training. 

You should:
- Ask specific technical questions about AWS services like VMware Cloud on AWS, EC2, EBS, and migration tools
- Express concerns about licensing costs, data transfer, and ongoing operational expenses
- Inquire about migration timelines, potential downtime, and rollback procedures
- Be knowledgeable about your current infrastructure but cautious about making the switch
- Show interest in hybrid solutions and gradual migration approaches
- Keep responses conversational and realistic, 2-3 sentences typically
- Start the conversation by introducing your situation and asking an opening question""",
            
            'situational-fluency': """You are a technical decision maker and IT director at a company considering cloud adoption. You have realistic concerns about security, compliance, cost optimization, vendor lock-in, and integration with existing systems.

You should:
- Challenge the AWS salesperson with thoughtful, well-informed questions
- Ask about implementation complexity, staff training requirements, and ongoing support
- Express concerns about data sovereignty, compliance requirements, and security controls
- Inquire about long-term strategy, pricing predictability, and exit strategies
- Be engaged and interested but appropriately skeptical and thorough in your evaluation
- Keep responses conversational, 2-3 sentences typically
- Start by introducing your role and primary concerns""",
            
            'smb-prospecting': """You are the owner/manager of a growing small business (50-100 employees) currently using basic on-premises IT infrastructure. You're interested in cloud solutions to improve efficiency and reduce IT overhead, but you need simple explanations and are very cost-conscious.

You should:
- Ask practical questions about implementation, ongoing costs, and day-to-day operations
- Express concerns about complexity, staff training, and whether cloud is right for your size business
- Inquire about what kind of support is available for smaller companies
- Focus on business benefits rather than technical details
- Be interested but need reassurance about costs, reliability, and ease of use
- Keep responses conversational and practical, 2-3 sentences typically
- Start by introducing your business and main challenges"""
        }
        
        return prompts.get(self.scenario, prompts['situational-fluency'])

    async def start_session(self):
        """Start Nova Sonic streaming session"""
        try:
            if not self.client:
                self._initialize_client()
            
            logger.info(f"Starting Nova Sonic session - Scenario: {self.scenario}, Voice: {self.voice_id}")
            
            # Initialize the bidirectional stream
            self.stream = await self.client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            self.is_active = True
            
            # Send session start event
            session_start = {
                "event": {
                    "sessionStart": {
                        "inferenceConfiguration": {
                            "maxTokens": 1024,
                            "topP": 0.9,
                            "temperature": 0.7
                        }
                    }
                }
            }
            await self.send_event(json.dumps(session_start))
            
            # Send prompt start event
            prompt_start = {
                "event": {
                    "promptStart": {
                        "promptName": self.prompt_name,
                        "textOutputConfiguration": {
                            "mediaType": "text/plain"
                        },
                        "audioOutputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": 24000,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "voiceId": self.voice_id,
                            "encoding": "base64",
                            "audioType": "SPEECH"
                        }
                    }
                }
            }
            await self.send_event(json.dumps(prompt_start))
            
            # Send system prompt
            text_content_start = {
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "SYSTEM",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        }
                    }
                }
            }
            await self.send_event(json.dumps(text_content_start))
            
            system_prompt = self.get_scenario_prompt()
            
            text_input = {
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name,
                        "content": system_prompt
                    }
                }
            }
            await self.send_event(json.dumps(text_input))
            
            text_content_end = {
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name
                    }
                }
            }
            await self.send_event(json.dumps(text_content_end))
            
            # Start processing responses
            self.response_task = asyncio.create_task(self._process_responses())
            
            logger.info("Nova Sonic session started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Nova Sonic session: {e}")
            self.is_active = False
            return False

    async def _process_responses(self):
        """Process responses from Nova Sonic stream"""
        try:
            while self.is_active:
                output = await self.stream.await_output()
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    
                    if 'event' in json_data:
                        # Handle content start event
                        if 'contentStart' in json_data['event']:
                            content_start = json_data['event']['contentStart']
                            self.role = content_start['role']
                            
                            if 'additionalModelFields' in content_start:
                                try:
                                    additional_fields = json.loads(content_start['additionalModelFields'])
                                    if additional_fields.get('generationStage') == 'SPECULATIVE':
                                        self.display_assistant_text = True
                                    else:
                                        self.display_assistant_text = False
                                except:
                                    self.display_assistant_text = False
                        
                        # Handle text output
                        elif 'textOutput' in json_data['event']:
                            text = json_data['event']['textOutput']['content']
                            
                            if (self.role == "ASSISTANT" and self.display_assistant_text):
                                # Send text to web interface
                                socketio.emit('ai_text', {
                                    'text': text,
                                    'session_id': self.session_id
                                })
                                logger.info(f"AI Customer: {text}")
                            elif self.role == "USER":
                                # Send transcription to web interface
                                socketio.emit('user_text', {
                                    'text': text,
                                    'session_id': self.session_id
                                })
                                logger.info(f"User said: {text}")
                        
                        # Handle audio output
                        elif 'audioOutput' in json_data['event']:
                            audio_content = json_data['event']['audioOutput']['content']
                            audio_bytes = base64.b64decode(audio_content)
                            
                            # Send audio to web interface
                            socketio.emit('ai_audio', {
                                'audio': audio_content,
                                'session_id': self.session_id
                            })
                            
                            logger.info("Received audio output from Nova Sonic")
                            
        except Exception as e:
            logger.error(f"Error processing Nova Sonic responses: {e}")

    async def send_audio_chunk(self, audio_base64):
        """Send audio chunk to Nova Sonic"""
        try:
            if not self.is_active:
                return False
            
            # Start audio input if not already started
            if not hasattr(self, 'audio_input_started'):
                await self.start_audio_input()
                self.audio_input_started = True
            
            audio_event = {
                "event": {
                    "audioInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                        "content": audio_base64
                    }
                }
            }
            await self.send_event(json.dumps(audio_event))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}")
            return False

    async def start_audio_input(self):
        """Start audio input stream"""
        audio_content_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 16000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }
                }
            }
        }
        await self.send_event(json.dumps(audio_content_start))

    async def end_audio_input(self):
        """End audio input stream"""
        if hasattr(self, 'audio_input_started'):
            audio_content_end = {
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name
                    }
                }
            }
            await self.send_event(json.dumps(audio_content_end))
            delattr(self, 'audio_input_started')

    async def end_session(self):
        """End Nova Sonic session"""
        try:
            if not self.is_active:
                return
            
            self.is_active = False
            
            # End audio input if active
            await self.end_audio_input()
            
            # Send prompt end
            prompt_end = {
                "event": {
                    "promptEnd": {
                        "promptName": self.prompt_name
                    }
                }
            }
            await self.send_event(json.dumps(prompt_end))
            
            # Send session end
            session_end = {
                "event": {
                    "sessionEnd": {}
                }
            }
            await self.send_event(json.dumps(session_end))
            
            # Close stream
            if self.stream:
                await self.stream.input_stream.close()
            
            # Cancel response task
            if self.response_task and not self.response_task.done():
                self.response_task.cancel()
            
            logger.info("Nova Sonic session ended")
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")

# Global session manager
active_sessions = {}

# Flask routes
@app.route('/')
def index():
    """Serve the main interface"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'active_sessions': len(active_sessions),
        'timestamp': datetime.now().isoformat()
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to Nova Sonic'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Clean up any sessions for this client
    sessions_to_remove = []
    for session_id, session in active_sessions.items():
        if hasattr(session, 'client_id') and session.client_id == request.sid:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        asyncio.run(active_sessions[session_id].end_session())
        del active_sessions[session_id]

@socketio.on('start_session')
def handle_start_session(data):
    """Start a new Nova Sonic session"""
    try:
        scenario = data.get('scenario', 'vmware-migration')
        voice_id = data.get('voice', 'matthew')
        session_id = str(uuid.uuid4())
        
        logger.info(f"Starting session {session_id} for {request.sid}")
        
        # Create session
        session = NovaSonicSession(session_id, scenario, voice_id)
        session.client_id = request.sid
        active_sessions[session_id] = session
        
        # Start session in background
        def start_session_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(session.start_session())
            loop.close()
            
            if success:
                socketio.emit('session_started', {
                    'session_id': session_id,
                    'scenario': scenario,
                    'voice': voice_id
                }, room=request.sid)
            else:
                socketio.emit('session_error', {
                    'error': 'Failed to start Nova Sonic session'
                }, room=request.sid)
        
        thread = threading.Thread(target=start_session_async)
        thread.start()
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        emit('session_error', {'error': str(e)})

@socketio.on('send_audio')
def handle_send_audio(data):
    """Handle audio input from client"""
    try:
        session_id = data.get('session_id')
        audio_data = data.get('audio')
        
        if session_id not in active_sessions:
            emit('error', {'message': 'Session not found'})
            return
        
        session = active_sessions[session_id]
        
        # Send audio to Nova Sonic in background
        def send_audio_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(session.send_audio_chunk(audio_data))
            loop.close()
        
        thread = threading.Thread(target=send_audio_async)
        thread.start()
        
    except Exception as e:
        logger.error(f"Error handling audio: {e}")
        emit('error', {'message': str(e)})

@socketio.on('end_session')
def handle_end_session(data):
    """End Nova Sonic session"""
    try:
        session_id = data.get('session_id')
        
        if session_id in active_sessions:
            session = active_sessions[session_id]
            
            # End session in background
            def end_session_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(session.end_session())
                loop.close()
            
            thread = threading.Thread(target=end_session_async)
            thread.start()
            
            del active_sessions[session_id]
            emit('session_ended', {'session_id': session_id})
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    # Check AWS credentials
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        logger.error("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        exit(1)
    
    logger.info("Starting Nova Sonic App Runner application...")
    
    # Get port from environment (App Runner sets this)
    port = int(os.environ.get('PORT', 8080))
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
