# Google OAuth Setup Guide

This guide explains how to set up Google OAuth authentication for the Issue Tracker. You'll need to create OAuth credentials in Google Cloud Console (not an API key - OAuth uses Client ID and Client Secret).

## Prerequisites

- A Google account
- Access to Google Cloud Console
- A Google Cloud project (or create a new one)

## Step-by-Step Setup

### 1. Create OAuth Credentials in Google Cloud Console

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Select or Create a Project**
   - Click the project dropdown at the top
   - Click "New Project" if needed
   - Name it (e.g., "AlphaFusion Issue Tracker")
   - Click "Create"

3. **Enable Google+ API** (or Google Identity API)
   - Go to "APIs & Services" → "Library"
   - Search for "Google+ API" or "Google Identity"
   - Click on it and click "Enable"

4. **Configure OAuth Consent Screen**
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "Internal" (if you have Google Workspace) or "External"
   - Fill in required fields:
     - App name: "AlphaFusion Issue Tracker"
     - User support email: your email
     - Developer contact: your email
   - Click "Save and Continue"
   - Skip scopes (click "Save and Continue")
   - Skip test users (click "Save and Continue")
   - Review and click "Back to Dashboard"

5. **Create OAuth Client ID**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Name: "Issue Tracker Web Client"
   - **Authorized redirect URIs**: Add these:
     ```
     http://localhost:6002/oauth/callback
     http://localhost:6001/oauth/callback
     https://your-production-domain.com/oauth/callback
     ```
     (Replace with your actual production URL)
   - Click "Create"
   PS: 667557036006-o3f9sac9895un6u6s1bjd5tb7esg16s9.apps.googleusercontent.com

6. **Copy Credentials**
   - You'll see a popup with:
     - **Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
     - **Client Secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)
   - **Save these securely** - you'll need them for configuration

### 2. Configure Credentials in Issue Tracker

You have two options for providing credentials:

#### Option A: Environment Variables (Easiest for Development)

Set these environment variables:

```bash
export GOOGLE_CLIENT_ID="your-client-id-here"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

Or in your `.env` file:
```bash
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

#### Option B: SecureConfigLoader (Recommended for Production)

**Method 1: JSON File (Easiest)**

Create a JSON file at `.credentials/app/issuetracker/google-issuetracker.json`:

```json
{
    "GOOGLE_CLIENT_ID": "your-client-id-here",
    "GOOGLE_CLIENT_SECRET": "your-client-secret-here"
}
```

The app will automatically load credentials from this file via SecureConfigLoader.

**Method 2: Individual Keys via SecureConfigLoader**

1. **Add to Redis/Consul Configuration**
   - Set these keys in your configuration system:
     - `app/issuetracker/google_client_id` → Your Client ID
     - `app/issuetracker/google_client_secret` → Your Client Secret

2. **Or add to config mapping file**
   - The `config_mapping.json` already includes these as sensitive keys
   - They will be loaded from `.credentials/` directory or Redis

### 3. Verify Configuration

1. **Start the Issue Tracker**
   ```bash
   docker-compose up -d issuetracker
   ```

2. **Check Logs**
   ```bash
   docker-compose logs issuetracker | grep -i oauth
   ```
   
   You should see:
   ```
   Google OAuth initialized
   ```
   
   If you see:
   ```
   Google OAuth credentials not configured
   ```
   Then credentials are missing - check your configuration.

3. **Test Login**
   - Go to `http://localhost:6002/login`
   - Enter a `@quantory.app` email
   - You should be redirected to Google for authentication

## Important Notes

### Authorized Redirect URIs

Make sure your redirect URI matches exactly:
- **Development**: `http://localhost:6002/oauth/callback`
- **Production**: `https://your-domain.com/oauth/callback`

The port and protocol must match exactly. If you're running on a different port, update both:
1. The redirect URI in Google Cloud Console
2. The Flask app port configuration

### Domain Restriction

The Issue Tracker only allows `@quantory.app` email addresses. When users authenticate with Google:
1. They must use a Google account with a `@quantory.app` email
2. The OAuth callback will verify the email domain
3. Non-quantory.app emails will be rejected

### Security Best Practices

1. **Never commit credentials to git**
   - Use environment variables or SecureConfigLoader
   - Add `.env` to `.gitignore`

2. **Use different credentials for dev/prod**
   - Create separate OAuth clients for each environment
   - Use different redirect URIs

3. **Rotate credentials periodically**
   - Regenerate Client Secret if compromised
   - Update configuration immediately

## Troubleshooting

### "Google OAuth not configured"
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Verify they're not empty strings
- Check application logs for errors

### "Redirect URI mismatch"
- Verify the redirect URI in Google Cloud Console matches exactly
- Check protocol (http vs https)
- Check port number
- Check path (`/oauth/callback`)

### "Access denied - Only @quantory.app users allowed"
- User authenticated successfully but email is not `@quantory.app`
- This is expected behavior - only quantory.app emails are allowed

### OAuth popup shows "Access blocked"
- Check OAuth consent screen configuration
- Verify app is published (for external apps)
- Check if test users are required (for external apps in testing)

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Authlib Documentation](https://docs.authlib.org/)

