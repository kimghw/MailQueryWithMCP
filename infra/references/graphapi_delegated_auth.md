Alright, let's extract only the Python content and present it in English.

---

## Practical Code Example for Developers: Python (Flask Web Application with MSAL)

This example demonstrates how to integrate the Microsoft Graph API into a Python Flask web application to authenticate users and retrieve emails using delegated permissions and the authorization code flow.

### App Registration Setup:

* Register your application in **Microsoft Entra ID**.
* Configure a **Web platform Redirect URI** (e.g., `http://localhost:5000/redirect`).
* Add `Mail.Read` (or `Mail.ReadBasic`) and `User.Read` **delegated permissions**. If refresh tokens are needed for long-term sessions, ensure the `offline_access` scope is also requested.
* Generate a **client secret** for your web application.

### Dependencies:

* Flask, requests, python-dotenv, msal.

### Configuration (.env and app\_config.py):

* Store `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` (e.g., `common`), `REDIRECT_URI`, `SCOPE` (e.g., `User.Read Mail.Read offline_access`) in a `.env` file.
* Load these settings into your Flask app's configuration.

### Authentication Flow (Conceptual):

* When a user initiates login, they are redirected to the Microsoft Identity Platform's `/authorize` endpoint with necessary parameters (`client_id`, `response_type=code`, `redirect_uri`, `scope`, `state`). This is typically handled by MSAL.
* Upon successful authentication and consent, Microsoft Entra ID redirects the user back to your `redirect_uri` with an authorization `code`.
* A Flask application route handling the `redirect_uri` captures this `code`.
* MSAL is then used to send a POST request to the `/token` endpoint, including the `client_secret`, to exchange the `code` for an `access_token` and `refresh_token`.
* The `access_token` and `refresh_token` are securely stored (e.g., in the session for a web app).

### Retrieving Emails via Microsoft Graph API Call:

* Define a Flask route (e.g., `/get_emails`).
* Within this route, retrieve the stored `access_token`.
* Construct the Graph API URL for messages: `https://graph.microsoft.com/v1.0/me/messages`.
* Optionally, add OData query parameters to filter, select, or sort emails. For example, to get the subject and sender of the top 5 unread messages: `https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false&$select=from,subject,receivedDateTime&$orderby=receivedDateTime desc&$top=5`.
* Send an HTTP GET request using the `requests` library, including the `access_token` in the `Authorization: Bearer <access_token>` header.
* Process the JSON response, which contains a collection of message objects.

### Example Code Snippet:

```python
# app.py (simplified)
import os
import requests
from flask import Flask, redirect, url_for, session, render_template, request
from msal import ConfidentialClientApplication

# --- Configuration (from .env or app_config.py) ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID") # e.g., 'common' or your tenant ID
REDIRECT_URI = os.getenv("REDIRECT_URI")
GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "User.Read Mail.Read offline_access").split()
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/"

app = Flask(__name__)
app.secret_key = os.urandom(24) # Replace with a strong, permanent key

# Initialize MSAL ConfidentialClientApplication
msal_app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

@app.route("/login")
def login():
    # Step 1: Redirect to the authorization endpoint
    auth_url = msal_app.get_authorization_request_url(
        GRAPH_SCOPES,
        redirect_uri=REDIRECT_URI,
        state=session.get("state", os.urandom(16).hex()) # Use a unique state
    )
    session["state"] = request.args.get('state', None) # Store state for validation
    return redirect(auth_url)

@app.route("/redirect")
def auth_redirect():
    # Step 2: Handle the redirect and acquire token
    if request.args.get('state') != session.get("state"):
        return "State mismatch!", 400 # CSRF protection

    # Acquire token using the authorization code
    result = msal_app.acquire_token_by_authorization_code(
        request.args['code'],
        GRAPH_SCOPES,
        redirect_uri=REDIRECT_URI
    )

    if "access_token" in result:
        session["access_token"] = result["access_token"]
        session["user"] = msal_app.acquire_token_silent(GRAPH_SCOPES, account=result["account"])["id_token_claims"]["name"]
        if "refresh_token" in result:
            session["refresh_token"] = result["refresh_token"]
        return redirect(url_for("index"))
    else:
        return f"Authentication failed: {result.get('error_description', result.get('error'))}"

@app.route("/get_emails")
def get_emails():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("login")) # Re-authenticate if no token

    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }

    # Example: Get top 5 messages, select specific fields, filter unread messages
    # URL: https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false&$select=from,subject,receivedDateTime&$orderby=receivedDateTime desc&$top=5
    mail_api_url = f"{GRAPH_API_ENDPOINT}me/messages?$filter=isRead eq false&$select=from,subject,receivedDateTime&$orderby=receivedDateTime desc&$top=5"

    try:
        response = requests.get(mail_api_url, headers=headers, timeout=30)
        response.raise_for_status() # Raise HTTPError for 4xx or 5xx responses
        emails = response.json().get('value', [])
        return render_template("emails.html", emails=emails)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token expired or invalid, attempt to refresh or re-authenticate
            # For simplicity, redirect to login. In production, use refresh token.
            return redirect(url_for("login")) 
        return f"Graph API call error: {e.response.status_code} - {e.response.text}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

### Python Console App (Device Code Flow) Note:

While the user requested the "authorization code flow," some Python examples follow the device code flow. This flow is suitable for headless devices or CLI tools. However, it's explicitly stated that the code implementation for the "list inbox" feature is not provided. To achieve email listing in a console app, you would need to combine the authentication portion (using `DeviceCodeCredential` and `GraphServiceClient`) with the mail API call structure (e.g., `user_client.me.messages.get()`).