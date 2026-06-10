import socketio
from ..logger import logger

# Initialize AsyncServer for ASGI
# We allow all origins for the sake of the example, but in production this should be locked down.
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    # Here you would typically authenticate the user via tokens in the query string or headers
    # Example: tech_id = environ.get('HTTP_X_TECH_ID')
    # For now, we will assume clients pass their tech_id in the connection handshake query string.
    query_string = environ.get('QUERY_STRING', '')
    tech_id = None
    for param in query_string.split('&'):
        if param.startswith('tech_id='):
            tech_id = param.split('=')[1]
    
    if tech_id:
        await sio.enter_room(sid, str(tech_id))
        logger.info(f"Socket.io client connected: {sid} mapped to tech_id {tech_id}")
    else:
        logger.warning(f"Socket.io client connected without tech_id: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Socket.io client disconnected: {sid}")

async def emit_notification(tech_id: str, payload: dict):
    """
    Emit a real-time notification to a specific technician.
    """
    try:
        await sio.emit('new_notification', payload, room=str(tech_id))
        logger.info(f"Emitted real-time notification to tech_id: {tech_id}")
    except Exception as e:
        logger.error(f"Failed to emit socket.io notification to {tech_id}: {e}")
