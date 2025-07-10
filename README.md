# Nova Sonic Sales Training - App Runner Deployment

## 🚀 **True Nova Sonic Experience**

This App Runner deployment provides **real bidirectional streaming** with Amazon Nova Sonic - the way it was designed to work!

## ✨ **What You Get:**

- **🎤 Real Speech-to-Speech** - Direct audio streaming to Nova Sonic
- **🔄 Bidirectional Streaming** - True real-time conversation
- **🎯 Sales Training Scenarios** - VMware, Situational Fluency, SMB
- **🔊 Professional Voices** - Native Nova Sonic voice synthesis
- **📝 Real-time Transcription** - See what you and AI said
- **🌐 Web Interface** - Easy to use browser interface

## 📦 **Package Contents:**

- `app.py` - Flask/SocketIO server with Nova Sonic integration
- `templates/index.html` - Web interface for speech training
- `requirements.txt` - Python dependencies
- `apprunner.yaml` - App Runner configuration
- `README.md` - This file

## 🎯 **App Runner Deployment Steps:**

### **Step 1: Create Deployment Package**
1. **Zip the entire folder:**
   - `nova-sonic-apprunner.zip`
   - Include all files: `app.py`, `templates/`, `requirements.txt`, `apprunner.yaml`

### **Step 2: Deploy via App Runner Console**

1. **Go to AWS App Runner Console**
   - Navigate to: https://console.aws.amazon.com/apprunner/

2. **Create Service**
   - Click **"Create service"**
   - Choose **"Source code repository"**

3. **Upload Source Code**
   - **Repository type**: Upload source code
   - **Upload**: `nova-sonic-apprunner.zip`
   - **Runtime**: Python 3

4. **Configure Service**
   - **Service name**: `nova-sonic-training`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `python app.py`
   - **Port**: `8080`

5. **Set Environment Variables**
   - **AWS_ACCESS_KEY_ID**: Your AWS access key
   - **AWS_SECRET_ACCESS_KEY**: Your AWS secret key
   - **AWS_DEFAULT_REGION**: `us-east-1`
   - **PORT**: `8080`

6. **Configure Auto Scaling**
   - **Min instances**: 1
   - **Max instances**: 3
   - **Concurrency**: 100

7. **Deploy**
   - Click **"Create & deploy"**
   - Wait for deployment (5-10 minutes)
   - Note the **App Runner URL**

### **Step 3: Access Your Application**

1. **Open the App Runner URL** (e.g., `https://abc123.us-east-1.awsapprunner.com`)
2. **Select training scenario**
3. **Choose AI voice**
4. **Start Nova Sonic session**
5. **Click and hold microphone** to speak
6. **Experience real speech-to-speech training!**

## 🎯 **Key Differences from Lambda:**

| Feature | Lambda Approach | App Runner + Nova Sonic |
|---------|----------------|------------------------|
| **Audio Processing** | Speech→Text→AI→Text→Speech | Direct Audio→Audio |
| **Latency** | ~2-3 seconds | ~500ms |
| **Conversation Flow** | Choppy request/response | Natural real-time |
| **Voice Quality** | Browser TTS + Polly | Native Nova Sonic voices |
| **Context** | Limited session memory | Full conversation context |
| **Realism** | Artificial feel | Natural conversation |

## 🔧 **Troubleshooting:**

### **Common Issues:**

1. **"AWS credentials not found"**
   - Ensure environment variables are set in App Runner
   - Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

2. **"Nova Sonic model not found"**
   - Ensure your AWS account has Nova Sonic access
   - Check region is set to us-east-1

3. **"WebSocket connection failed"**
   - Check App Runner service is running
   - Verify port 8080 is configured

4. **"Microphone not working"**
   - Allow microphone permissions in browser
   - Use HTTPS (App Runner provides this automatically)

### **Debug Steps:**

1. **Check App Runner Logs**
   - Go to App Runner Console
   - Click on your service
   - View "Logs" tab for errors

2. **Test Health Endpoint**
   - Visit: `https://your-app-url/health`
   - Should show service status

3. **Browser Console**
   - Open browser developer tools
   - Check for JavaScript errors

## 🎉 **Expected Experience:**

1. **Natural Conversation Flow** - Like talking to a real customer
2. **Instant Responses** - Nova Sonic responds in real-time
3. **Professional Audio** - High-quality voice synthesis
4. **Context Awareness** - AI remembers entire conversation
5. **Realistic Training** - True-to-life sales scenarios

## 💡 **Tips for Best Experience:**

- **Use headphones** to prevent audio feedback
- **Speak clearly** for best recognition
- **Wait for AI to finish** before responding
- **Practice different scenarios** to improve skills
- **Use in quiet environment** for best audio quality

This is the **real Nova Sonic experience** - true bidirectional speech streaming for realistic sales training!
