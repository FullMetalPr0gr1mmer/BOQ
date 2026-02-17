import os
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AZURE_APPLICATION_ID")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_VALUE")

TARGET_USER = "nour.tarek.ext@nokia.com"
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "done")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Authenticate ---
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

token_response = app.acquire_token_for_client(
    scopes=["https://graph.microsoft.com/.default"]
)

if "access_token" not in token_response:
    print("Authentication failed!")
    print(token_response.get("error_description", token_response))
    exit(1)

access_token = token_response["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}
print("Authenticated successfully.\n")

# --- Check token roles ---
import base64, json
payload = access_token.split(".")[1]
payload += "=" * (4 - len(payload) % 4)  # fix padding
decoded = json.loads(base64.b64decode(payload))
print("Token roles (permissions):", decoded.get("roles", "NONE"))
print()

# --- Check if user exists ---
print(f"Checking user: {TARGET_USER}")
user_resp = requests.get(
    f"https://graph.microsoft.com/v1.0/users/{TARGET_USER}",
    headers=headers,
)
if user_resp.status_code == 200:
    u = user_resp.json()
    print(f"  Found: {u.get('displayName')} (ID: {u.get('id')})")
else:
    print(f"  User lookup failed ({user_resp.status_code}): {user_resp.json().get('error', {}).get('message', '')}")
print()

# --- List files in target user's OneDrive root ---
print(f"Listing OneDrive files for: {TARGET_USER}")
resp = requests.get(
    f"https://graph.microsoft.com/v1.0/users/{TARGET_USER}/drive/root/children",
    headers=headers,
)

if resp.status_code != 200:
    print(f"Failed ({resp.status_code}):")
    print(resp.json())
    exit(1)

items = resp.json().get("value", [])
print(f"Found {len(items)} items:\n")
for item in items:
    item_type = "folder" if "folder" in item else "file"
    size = item.get("size", 0)
    print(f"  - {item['name']}  ({item_type}, {size:,} bytes)")

print("\nDone!")
