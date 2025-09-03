# main.py
import socketio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import json
from datetime import datetime
import os

# --- Redis Configuration ---
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = None

# --- FastAPI and Socket.IO Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # or specifically ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
asgi_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=app)

# --- Redis Functions ---
async def get_redis_client():
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client

async def store_message(room: str, username: str, message: str):
    """Store a message in Redis"""
    try:
        redis_client = await get_redis_client()
        message_data = {
            'username': username,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        # Store in room-specific list (limited to last 100 messages)
        await redis_client.lpush(f"room:{room}:messages", json.dumps(message_data))
        await redis_client.ltrim(f"room:{room}:messages", 0, 99)
        
        # Set expiration for room data (24 hours)
        await redis_client.expire(f"room:{room}:messages", 86400)
        
        return True
    except Exception as e:
        print(f"Error storing message in Redis: {e}")
        return False

async def get_room_history(room: str, limit: int = 50):
    """Get message history for a room"""
    try:
        redis_client = await get_redis_client()
        messages = await redis_client.lrange(f"room:{room}:messages", 0, limit - 1)
        
        # Parse and reverse messages to show oldest first
        parsed_messages = []
        for msg in reversed(messages):
            try:
                parsed_messages.append(json.loads(msg))
            except json.JSONDecodeError:
                continue
                
        return parsed_messages
    except Exception as e:
        print(f"Error getting room history from Redis: {e}")
        return []

# --- FastAPI Routes ---
@app.get("/")
async def read_root():
    # Serve the client-side HTML file
    with open('index.html') as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/stats")
async def get_stats():
    """
    A debugging endpoint to see the current state of rooms and clients.
    """
    # Get the dictionary of rooms for the default namespace '/'
    rooms_data = sio.manager.rooms.get('/', {})
    
    # We want to filter out the private rooms that Socket.IO creates for each client
    # (where the room name is the same as the client's SID).
    active_rooms = {}
    for room_name, sids in rooms_data.items():
        # A simple check: if the room name is not a session ID, it's a "real" room.
        # This works because SIDs are long, random strings.
        if len(room_name) < 20: 
            active_rooms[room_name] = list(sids)
            
    return {"active_rooms": active_rooms}

@app.get("/api/rooms/{room}/history")
async def get_room_messages(room: str, limit: int = 50):
    """API endpoint to get message history for a room"""
    messages = await get_room_history(room, limit)
    return {"messages": messages}

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ, auth):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.on('join')
async def handle_join(sid, data):
    room = data.get('room')
    username = data.get('username', 'Anonymous')
    if not room:
        return
    
    # Join the room using Socket.IO
    await sio.enter_room(sid, room)
    
    print(f"Client {sid} ({username}) joined room: {room}")
    
    # Get room history and send to the joining user
    room_history = await get_room_history(room)
    await sio.emit('room_history', {'messages': room_history}, to=sid)
    
    # Notify others in the room
    await sio.emit('user_joined', {'username': username}, room=room, skip_sid=sid)
    
    # Confirm join to the user
    await sio.emit('join_success', {'room': room}, to=sid)

@sio.on('leave')
async def handle_leave(sid, data):
    room = data.get('room')
    if not room:
        return
        
    # Leave the room using Socket.IO
    await sio.leave_room(sid, room)
    
    print(f"Client {sid} left room: {room}")
    
    # Notify others in the room
    await sio.emit('user_left', {'username': 'A user'}, room=room)

@sio.on('message')
async def handle_message(sid, data):
    room = data.get('room')
    message = data.get('message')
    username = data.get('username')
    
    if not room or not message:
        return
        
    print(f"Message from {sid} username=> {username} in room {room}: {message}")
    
    # Store message in Redis
    await store_message(room, username, message)
    
    # Send message to ALL OTHER users in the room
    await sio.emit('new_message', {
        'sender': username, 
        'message': message,
        'timestamp': datetime.now().isoformat()
    }, room=room, skip_sid=sid)

# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup"""
    try:
        await get_redis_client()
        print("Connected to Redis successfully")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()
        print("Redis connection closed")