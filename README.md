# Python Socket.IO Chat with Redis Message History

A real-time multi-room chat application built with FastAPI, Socket.IO, and Redis for persistent message storage.

## Features

- Real-time messaging using Socket.IO
- Multi-room chat support
- Persistent message history stored in Redis
- Modern, responsive UI
- Message timestamps
- User join/leave notifications

## Prerequisites

- Docker and Docker Compose
- Python 3.8+

## Setup Instructions

### 1. Start Redis Container

```bash
docker-compose up -d
```

This will start a Redis container on port 6379 with persistent storage.

### 2. Install Python Dependencies

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application

```bash
uvicorn main:asgi_app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the Application

Open your browser and navigate to `http://localhost:8000`

## Architecture

- **FastAPI**: Web framework for HTTP endpoints
- **Socket.IO**: Real-time bidirectional communication
- **Redis**: In-memory data store for message persistence
- **Docker**: Containerized Redis for easy deployment

## API Endpoints

- `GET /`: Main chat interface
- `GET /stats`: Debug endpoint showing active rooms and clients
- `GET /api/rooms/{room}/history`: Get message history for a specific room

## Socket.IO Events

- `join`: Join a chat room
- `leave`: Leave a chat room
- `message`: Send a message to a room
- `user_joined`: Notification when a user joins
- `user_left`: Notification when a user leaves
- `room_history`: Receive message history when joining

## Redis Data Structure

Messages are stored in Redis using the key pattern: `room:{room_name}:messages`

- Each room has a list of messages (limited to last 100)
- Messages include: username, message content, timestamp, and room name
- Data expires after 24 hours to prevent unlimited growth

## Environment Variables

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)

## Development

To modify the application:

1. Make changes to `main.py` for backend logic
2. Update `index.html` for frontend changes
3. Restart the server to see changes

## Troubleshooting

- Ensure Redis container is running: `docker-compose ps`
- Check Redis logs: `docker-compose logs redis`
- Verify Redis connection: `docker exec -it chat-redis redis-cli ping`
