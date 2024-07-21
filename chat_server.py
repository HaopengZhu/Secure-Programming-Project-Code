import asyncio
import websockets
import json
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

CHUNK_SIZE = 190

connected_clients = {}
client_public_keys = {}

server_ip = os.getenv('SERVER_IP', '0.0.0.0')
server_port = int(os.getenv('SERVER_PORT', 5555))

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

async def register(websocket):
    try:
        name_message = await websocket.recv()
        name_data = json.loads(name_message)
        name = name_data["id"]
        connected_clients[name] = websocket
        print(f"Client registered: {name}")
        
        await websocket.send(public_pem)
        await broadcast_presence()
    except json.JSONDecodeError:
        print("Error decoding JSON during registration")
        await websocket.close()

async def unregister(websocket):
    for name, client in connected_clients.items():
        if client == websocket:
            del connected_clients[name]
            print(f"Client unregistered: {name}")
            break
    await broadcast_presence()

async def broadcast(message):
    for client in connected_clients.values():
        await client.send(message)

async def broadcast_presence():
    presence_message = json.dumps({"tag": "presence", "presence": [{"nickname": name, "jid": f"{name}@Server1"} for name in connected_clients]})
    await broadcast(presence_message)

def encrypt_chunk(chunk, public_key):
    return public_key.encrypt(
        chunk.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

async def handle_message(websocket, path):
    try:
        await register(websocket)
        async for message in websocket:
            if not message:
                continue
            try:
                print(f"Received message: {message}")
                message_data = json.loads(message)
            except json.JSONDecodeError:
                print("Error decoding JSON message")
                continue

            try:
                if message_data["tag"] in ["message", "raw_message"]:
                    recipient = connected_clients.get(message_data["to"])
                    if recipient:
                        if message_data["tag"] == "message":
                            chunks = [message_data["info"][i:i + CHUNK_SIZE].encode() for i in range(0, len(message_data["info"]), CHUNK_SIZE)]
                            encrypted_chunks = [encrypt_chunk(chunk, client_public_keys[message_data["to"]]) for chunk in chunks]
                            for chunk in encrypted_chunks:
                                await recipient.send(json.dumps({"tag": "message", "from": message_data["from"], "to": message_data["to"], "info": chunk.hex()}))
                        else:
                            await recipient.send(json.dumps({"tag": "raw_message", "from": message_data["from"], "to": message_data["to"], "info": message_data["info"]}))
                        print(f"Forwarded message to {message_data['to']}")
                    else:
                        print(f"Recipient {message_data['to']} not found")
            except Exception as e:
                print(f"Error processing message: {e}")

            if message_data["tag"] == "check":
                await websocket.send(json.dumps({"tag": "checked"}))
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in connection handler: {e}")
    finally:
        await unregister(websocket)

try:
    start_server = websockets.serve(handle_message, server_ip, server_port)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()
except OSError as e:
    print(f"Error starting server: {e}")















