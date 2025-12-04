# OAuth 2.0 Setup Guide for Jiraone

This guide walks you through setting up OAuth 2.0 (3LO) authentication to use jiraone with Atlassian Cloud.

## Prerequisites

- An Atlassian Cloud account with admin access
- Access to the [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
- Python 3.9+ with jiraone installed

## Step 1: Create an OAuth 2.0 App

1. Go to the [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
2. Click **Create** → **OAuth 2.0 integration**
3. Enter a name for your app (e.g., "My Jiraone App")
4. Accept the terms and click **Create**

## Step 2: Configure Permissions (Scopes)

1. In your app settings, go to **Permissions**
2. Click **Add** next to **Jira API**
3. Configure the scopes your app needs:

### Common Scopes

| Scope | Description |
|-------|-------------|
| `read:jira-work` | Read project and issue data |
| `write:jira-work` | Create and edit issues |
| `read:jira-user` | Read user information |
| `manage:jira-project` | Manage project settings |
| `manage:jira-configuration` | Manage Jira configuration |

4. Click **Save changes**

## Step 3: Configure Authorization

1. Go to **Authorization** in your app settings
2. Click **Add** next to **OAuth 2.0 (3LO)**
3. Enter a **Callback URL** (e.g., `http://localhost:8000/callback`)
   - For development, you can use `http://localhost:8000/callback`
   - For production, use your actual application URL
4. Click **Save changes**

## Step 4: Get Your Client Credentials

1. Go to **Settings** in your app
2. Copy your:
   - **Client ID**
   - **Client Secret** (click "Show" to reveal)

Keep these secure! Never commit them to version control.

## Step 5: Construct the Authorization URL

Your authorization URL follows this format:

```
https://auth.atlassian.com/authorize
  ?audience=api.atlassian.com
  &client_id=YOUR_CLIENT_ID
  &scope=read:jira-work%20write:jira-work%20offline_access
  &redirect_uri=http://localhost:8000/callback
  &state=YOUR_STATE_VALUE
  &response_type=code
  &prompt=consent
```

**Important**: Include `offline_access` scope to get a refresh token.

## Step 6: Using OAuth with Jiraone

### Initial Authentication

```python
from jiraone import LOGIN

# Configure OAuth credentials
oauth_config = {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "callback_url": "https://auth.atlassian.com/authorize?audience=api.atlassian.com"
                    "&client_id=YOUR_CLIENT_ID"
                    "&scope=read:jira-work%20write:jira-work%20offline_access"
                    "&redirect_uri=http://localhost:8000/callback"
                    "&state={YOUR_USER_BOUND_VALUE}"
                    "&response_type=code"
                    "&prompt=consent",
    "name": "your-instance"  # Optional: specific instance name
}

# Initialize OAuth session
LOGIN(oauth=oauth_config)

# Follow the prompts:
# 1. Click the printed authorization URL
# 2. Authorize the app in your browser
# 3. Copy the redirect URL and paste it back
```

### Saving and Reusing Tokens

```python
from jiraone import LOGIN
import json

# After initial auth, save the token
oauth_token = LOGIN.save_oauth  # Returns dict with tokens

# Store securely (e.g., database, encrypted file)
with open('token.json', 'w') as f:
    json.dump(oauth_token, f)

# Later, reload the token
with open('token.json', 'r') as f:
    saved_token = json.load(f)

# Set the saved token before re-initializing
LOGIN.save_oauth = json.dumps(saved_token)

# Re-initialize with oauth (will use refresh token)
LOGIN(oauth=oauth_config)
```

### Making API Requests

```python
from jiraone import LOGIN, endpoint

# After OAuth initialization
response = LOGIN.get(endpoint.myself())
print(response.json())

# Get all projects
projects = LOGIN.get(endpoint.get_projects())
print(projects.json())
```

## Token Lifecycle

### Access Tokens
- Valid for **1 hour**
- Used for API requests via Bearer authentication

### Refresh Tokens
- Valid for **90 days** (if not used)
- Used to obtain new access tokens
- Jiraone automatically refreshes tokens when needed

## Best Practices

### 1. Secure Credential Storage

```python
import os
from jiraone import LOGIN

# Use environment variables
oauth_config = {
    "client_id": os.environ.get("JIRA_CLIENT_ID"),
    "client_secret": os.environ.get("JIRA_CLIENT_SECRET"),
    "callback_url": os.environ.get("JIRA_CALLBACK_URL"),
}
```

### 2. Handle Token Expiration

```python
from jiraone import LOGIN
from jiraone.exceptions import JiraAuthenticationError

def make_request_with_retry(endpoint):
    try:
        return LOGIN.get(endpoint)
    except JiraAuthenticationError:
        # Token might be expired, re-authenticate
        LOGIN(oauth=oauth_config)
        return LOGIN.get(endpoint)
```

### 3. Use Environment-Specific Configurations

```python
import os

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    callback_url = "https://myapp.com/oauth/callback"
else:
    callback_url = "http://localhost:8000/callback"
```

## Troubleshooting

### "Invalid client" Error

- Verify your Client ID and Secret are correct
- Check that your app is active in the Developer Console

### "Invalid redirect_uri" Error

- Ensure the redirect URI in your request exactly matches the one configured in the Developer Console
- Check for trailing slashes or protocol mismatches

### "Scope not allowed" Error

- Verify you've added the required scopes in the Developer Console
- Some scopes require app approval from Atlassian

### Token Refresh Fails

- Refresh tokens expire after 90 days of inactivity
- If refresh fails, users need to re-authorize

## Security Considerations

1. **Never expose client secrets** in client-side code or public repositories
2. **Use HTTPS** for all callback URLs in production
3. **Validate state parameters** to prevent CSRF attacks
4. **Store tokens securely** using encryption at rest
5. **Implement token rotation** for long-running applications
6. **Log authentication events** for security auditing

## API Rate Limits

OAuth 2.0 requests are subject to Atlassian's rate limits:
- Normal rate limit: ~100 requests per minute
- Burst limit: May allow brief periods of higher traffic

Use jiraone's built-in retry logic to handle rate limit errors:

```python
from jiraone import LOGIN, RetryConfig, with_retry

@with_retry(config=RetryConfig(max_retries=3))
def get_all_issues():
    return LOGIN.get(endpoint.search_issues_jql(jql="project = TEST"))
```

## Additional Resources

- [Atlassian OAuth 2.0 Documentation](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Jira Cloud REST API Reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Developer Console](https://developer.atlassian.com/console/myapps/)
