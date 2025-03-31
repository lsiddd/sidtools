import base64
import hmac
import time
import struct
from urllib.parse import urlparse, parse_qs

def debug_print(label, value):
    print(f"[DEBUG] {label}:")
    print(f"        {value}\n")

def parse_totp_uri(uri):
    parsed = urlparse(uri)
    params = parse_qs(parsed.query)
    return {
        'secret': params['secret'][0],
        'algorithm': params.get('algorithm', ['SHA1'])[0],
        'digits': int(params.get('digits', [6])[0]),
        'period': int(params.get('period', [30])[0])
    }

def generate_totp_with_debug(secret_b32, algorithm, digits, period):
    # --- Step 1: Decode Base32 Secret ---
    secret_b32 = secret_b32.upper().replace('=', '')  # Normalize
    padding = (-len(secret_b32)) % 8  # Correct padding calculation
    secret = base64.b32decode(secret_b32 + '=' * padding)
    debug_print("Decoded secret (hex)", secret.hex())

    # --- Step 2: Calculate Time Step ---
    current_time = int(time.time())
    time_step = current_time // period
    debug_print("Time calculations", 
               f"Current Unix time: {current_time}\n"
               f"Time step ({period}sec): {time_step}")

    # --- Step 3: Pack Time Step ---
    time_step_bytes = struct.pack(">Q", time_step)
    debug_print("Packed time step", time_step_bytes.hex())

    # --- Step 4: Compute HMAC ---
    hmac_digest = hmac.new(secret, time_step_bytes, algorithm.lower()).digest()
    debug_print("HMAC digest", hmac_digest.hex())

    # --- Step 5: Dynamic Truncation ---
    offset = hmac_digest[-1] & 0x0F
    truncated = hmac_digest[offset:offset+4]
    debug_print("Truncation", 
               f"Last byte: 0x{hmac_digest[-1]:02x}\n"
               f"Offset: {offset}\n"
               f"Truncated bytes: {truncated.hex()}")

    # --- Step 6: Generate Code ---
    code_int = struct.unpack(">I", truncated)[0] & 0x7FFFFFFF
    code = code_int % (10 ** digits)
    debug_print("Final code", 
               f"31-bit integer: {code_int}\n"
               f"Formatted: {code:0{digits}d}")

    return f"{code:0{digits}d}"  # Fixed the missing closing brace

# --------------------------------------------------
# Valid Example (No Errors)
# --------------------------------------------------
totp_uri = r"otpauth://totp/Example%20Inc.:john%40example.com?issuer=Example%20Inc.&secret=LFLQHIQWE4J4V6WO&algorithm=SHA1&digits=6&period=30"

print("🔍 Parsing URI...")
params = parse_totp_uri(totp_uri)

print("\n📋 Parameters:")
print(f"Secret: {params['secret']}")
print(f"Algorithm: {params['algorithm']}")
print(f"Digits: {params['digits']}")
print(f"Period: {params['period']} sec\n")

print("🔐 Generating Code...")
code = generate_totp_with_debug(
    params['secret'], 
    params['algorithm'], 
    params['digits'], 
    params['period']
)

print(f"\n✅ Final Code: {code}")