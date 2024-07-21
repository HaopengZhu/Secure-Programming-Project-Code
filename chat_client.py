import asyncio
import websockets
import json
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

CHUNK_SIZE = 190

client_id = os.getenv('CLIENT_ID', 'Client1')
recipient_id = os.getenv('RECIPIENT_ID', 'Client2')

def decrypt_chunk(chunk, private_key):
    return private_key.decrypt(
        chunk,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

async def send_message(websocket):
    try:
        while True:
            message = input("Enter message: ")
            chunks = [message[i:i + CHUNK_SIZE] for i in range(0, len(message), CHUNK_SIZE)]
            for chunk in chunks:
                message_data = json.dumps({"tag": "message", "from": client_id, "to": recipient_id, "info": chunk})
                await websocket.send(message_data)
                print(f"Sent message: {message_data}")  # 添加发送日志
    except asyncio.CancelledError:
        pass

async def receive_message(websocket):
    try:
        while True:
            message = await websocket.recv()
            print(f"Received raw message: {message}")  # 添加接收日志
            message_data = json.loads(message)
            if message_data["tag"] == "message":
                encrypted_chunk = bytes.fromhex(message_data["info"])
                decrypted_chunk = decrypt_chunk(encrypted_chunk, private_key)
                print(f"Received: {decrypted_chunk.decode()}")
    except asyncio.CancelledError:
        pass

async def main():
    server_ip = input("Enter server IP address: ")
    server_port = input("Enter server port: ") or 5555  
    async with websockets.connect(f"ws://{server_ip}:{server_port}") as websocket:
        await websocket.send(json.dumps({"id": client_id}))  # 发送客户端ID作为JSON
        try:
            await asyncio.gather(send_message(websocket), receive_message(websocket))
        except asyncio.CancelledError:
            pass

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 使用 asyncio.run 替换 get_event_loop 以避免 DeprecationWarning
asyncio.run(main())






