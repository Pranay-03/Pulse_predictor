"""Load sample data into PPP database."""
import urllib.request
import urllib.parse
import http.cookiejar
import os

BASE = "http://127.0.0.1:8000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler(),
)

# Register all users (2 extra managers for diversity)
users = [
    ("Admin User", "admin@test.com", "admin123", "ADMIN"),
    ("Sarah Johnson", "manager@test.com", "manager123", "MANAGER"),
    ("Viewer User", "viewer@test.com", "viewer123", "VIEWER"),
    ("Mike Chen", "mike@test.com", "manager123", "MANAGER"),
    ("Priya Patel", "priya@test.com", "manager123", "MANAGER"),
]
for name, email, pwd, role in users:
    d = urllib.parse.urlencode({"name": name, "email": email, "password": pwd, "role": role}).encode()
    try:
        opener.open(urllib.request.Request(f"{BASE}/register", data=d, method="POST"))
        print(f"Registered {role}: {email}")
    except Exception as e:
        print(f"Register {email}: {e}")

# Login as admin
d = urllib.parse.urlencode({"email": "admin@test.com", "password": "admin123"}).encode()
opener.open(urllib.request.Request(f"{BASE}/login", data=d, method="POST"))
print("Logged in as admin")

# Upload CSV via multipart form
csv_path = os.path.join(os.path.dirname(__file__), "data", "sample_data.csv")
with open(csv_path, "rb") as f:
    csv_data = f.read()

boundary = "----PPPBoundary12345"
body = b""
body += f"--{boundary}\r\n".encode()
body += b'Content-Disposition: form-data; name="file"; filename="sample_data.csv"\r\n'
body += b"Content-Type: text/csv\r\n\r\n"
body += csv_data
body += f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"{BASE}/projects/upload",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
r = opener.open(req)
print(f"Upload complete! URL: {r.url}")

# Verify count
r = opener.open(f"{BASE}/projects")
content = r.read().decode()
# Count project rows
count = content.count("project-row")
print(f"Projects visible on dashboard: {count}")

# Check alerts
r = opener.open(f"{BASE}/alerts")
content = r.read().decode()
alert_count = content.count("accordion-item")
print(f"Alerts generated: {alert_count}")

print("\nDone! Visit http://127.0.0.1:8000 to see the data.")
