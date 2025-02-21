from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

# Predefined Users with Groups
USERS = [
    {"user_id": 1, "name": "Alice", "group_id": 1, "can_edit": True, "can_delete": False},
    {"user_id": 2, "name": "Bob", "group_id": 1, "can_edit": True, "can_delete": True},
    {"user_id": 3, "name": "Charlie", "group_id": 2, "can_edit": True, "can_delete": False},
    {"user_id": 4, "name": "David", "group_id": 2, "can_edit": True, "can_delete": True},
]

# Store active WebSocket connections per group
group_subscribers = {}

# In-memory storage for messages per group
group_messages = {}


# Kafka Producer Function
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    return producer


# Kafka Consumer for a Group
async def consume_group_messages(group_id):
    topic = f"group_{group_id}"
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, group_id=f"chat-group-{group_id}")
    await consumer.start()

    try:
        async for msg in consumer:
            message = json.loads(msg.value.decode())
            if group_id not in group_messages:
                group_messages[group_id] = []
            group_messages[group_id].append(message)
            await broadcast_group_message(group_id, message)
    finally:
        await consumer.stop()


# Start Kafka consumers for all groups on startup
@app.on_event("startup")
async def startup_event():
    for group in set(user["group_id"] for user in USERS):
        asyncio.create_task(consume_group_messages(group))


# Broadcast messages to WebSocket clients in the same group
async def broadcast_group_message(group_id, message):
    if group_id in group_subscribers:
        for ws in group_subscribers[group_id]:
            await ws.send_json(message)


# WebSocket Subscription for Group Messages
@app.websocket("/subscribe/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: int):
    await websocket.accept()

    if group_id not in group_subscribers:
        group_subscribers[group_id] = set()
    group_subscribers[group_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        group_subscribers[group_id].remove(websocket)


# Message Model
class Message(BaseModel):
    user_id: int
    message: str


# Send Message (Kafka Publish to Group)
@app.post("/send-message/")
async def send_message(data: Message):
    user = next((u for u in USERS if u["user_id"] == data.user_id), None)
    if not user:
        return {"error": "Invalid user ID"}

    group_id = user["group_id"]
    topic = f"group_{group_id}"

    message_data = {
        "id": len(group_messages.get(group_id, [])) + 1,
        "user_id": user["user_id"],
        "name": user["name"],
        "group_id": group_id,
        "message": data.message,
        "can_edit": user["can_edit"],
        "can_delete": user["can_delete"]
    }

    producer = await get_kafka_producer()
    await producer.send(topic, json.dumps(message_data).encode())
    await producer.stop()

    return {"status": "Message sent", "group_id": group_id}


# Get Messages for a Group
@app.get("/messages/{group_id}")
async def get_messages(group_id: int):
    return group_messages.get(group_id, [])


# Edit Message in a Group
@app.put("/edit-message/{message_id}")
async def edit_message(message_id: int, new_text: str, user_id: int):
    for group_id, messages in group_messages.items():
        for msg in messages:
            if msg["id"] == message_id and msg["user_id"] == user_id and msg["can_edit"]:
                msg["message"] = new_text
                await broadcast_group_message(group_id, msg)
                return {"status": "Message edited"}
    return {"error": "Edit not allowed"}


# Delete Message in a Group
@app.delete("/delete-message/{message_id}")
async def delete_message(message_id: int, user_id: int):
    for group_id, messages in group_messages.items():
        msg = next((m for m in messages if m["id"] == message_id), None)

        if msg and msg["user_id"] == user_id and msg["can_delete"]:
            group_messages[group_id] = [m for m in messages if m["id"] != message_id]
            await broadcast_group_message(group_id, {"id": message_id, "deleted": True})
            return {"status": "Message deleted"}

    return {"error": "Delete not allowed"}


# Get Users
@app.get("/users/")
async def get_users():
    return USERS
