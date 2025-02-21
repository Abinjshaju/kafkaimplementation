# Kafka FastAPI Chat

## Overview
This project is a real-time chat application using FastAPI and Kafka. It allows users to send messages within groups, with Kafka handling message distribution and WebSockets enabling real-time updates.

## Prerequisites
Ensure you have Kafka and Zookeeper installed and running.

### Start Kafka and Zookeeper:
```sh
# Start Zookeeper
zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka Server
kafka-server-start.sh config/server.properties
```

## Kafka Commands
Here are some useful Kafka commands to monitor and manage topics and messages:

### Create a Topic
```sh
kafka-topics.sh --create --topic group_1 --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### List Topics
```sh
kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Describe a Topic
```sh
kafka-topics.sh --describe --topic group_1 --bootstrap-server localhost:9092
```

### Send Messages to a Topic
```sh
echo '{"user_id": 1, "message": "Hello, Kafka!"}' | kafka-console-producer.sh --topic group_1 --bootstrap-server localhost:9092
```

### Read Messages from a Topic
```sh
kafka-console-consumer.sh --topic group_1 --bootstrap-server localhost:9092 --from-beginning
```

### Check Consumer Groups
```sh
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

### Describe a Consumer Group
```sh
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group chat-group-1
```

## Project Structure
- `main.py`: Contains FastAPI endpoints, WebSocket handling, Kafka producer, and consumer logic.

## API Endpoints
### Subscribe to a Group
```
GET ws://localhost:8000/subscribe/{group_id}
```
Connects to a WebSocket channel for real-time message updates.

### Send a Message
```
POST /send-message/
```
Sends a message to Kafka, which distributes it to the relevant group.

#### Request Body:
```json
{
  "user_id": 1,
  "message": "Hello!"
}
```

### Get Messages for a Group
```
GET /messages/{group_id}
```
Retrieves all messages for a specific group.

### Edit a Message
```
PUT /edit-message/{message_id}
```
Edits an existing message if the user has permission.

### Delete a Message
```
DELETE /delete-message/{message_id}
```
Deletes a message if the user has permission.

## Running the FastAPI Server
Start the FastAPI server with:
```sh
uvicorn main:app --reload
```

Now, your Kafka-powered real-time chat app is ready! 🚀

