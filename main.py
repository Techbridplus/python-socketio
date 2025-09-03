# main.py
import socketio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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
    
    # Send message to ALL OTHER users in the room
    await sio.emit('new_message', {
        'sender': username, 
        'message': message,
        'timestamp': 'now' # Consider using a real timestamp
    }, room=room, skip_sid=sid) # <-- Add skip_sid=sid HERE