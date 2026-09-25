import requests
import base64
from typing import Optional

custom_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Accept": "*/*",
    "Cache-Control": "no-cache, no-store",
}

def fetch_url(url: str, timeout: int = 15) -> str:
    response = requests.get(url=url, headers=custom_headers, timeout=timeout)
    response.raise_for_status()
    return response.text

# Generic decryption that matches the Kodi plugin logic - for your OWN encrypted M3Us
# This is NOT tied to Cricfy's private keys - you can generate your own
def decrypt_content_generic(content: str) -> str:
    content = content.strip()
    try:
        if content.startswith("#EXTM3U") or content.startswith("#EXTINF") or content.startswith("#KODIPROP"):
            return content
        if len(content) < 79:
            return content
        part1 = content[0:10]
        part2 = content[34:-54]
        part3 = content[-10:]
        encrypted_data_str = part1 + part2 + part3
        iv_base64 = content[10:34]
        key_base64 = content[-54:-10]
        iv = base64.b64decode(iv_base64)
        key = base64.b64decode(key_base64)
        encrypted_bytes = base64.b64decode(encrypted_data_str)
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import unpad
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(encrypted_bytes)
        decrypted_data = unpad(decrypted_padded, AES.block_size)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption failed, returning original: {e}")
        return content
