# Google sign-in setup

Email/password login remains available. Google login is disabled until the backend has its own OAuth credentials. Connecting Google to ChatGPT does not configure this application.

1. Open https://console.cloud.google.com/auth/overview and choose/create your project.
2. Configure Google Auth Platform branding and audience. For an external app in Testing, add your Google account under test users.
3. Create an OAuth client of type **Web application**.
4. Add this exact authorized redirect URI:
   `http://localhost:3000/api/v1/auth/google/callback`
5. Save these values in the project's local `.env` (never commit the secret or put it in frontend variables):

```dotenv
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/v1/auth/google/callback
```

6. Restart the backend. Open **http://localhost:3000** (not 127.0.0.1, since the callback cookie must return to the same host), then choose Continue with Google.

For production use your actual HTTPS origin for the callback, register that exact URI with Google, set SECURE_COOKIES=true, and set ALLOWED_ORIGINS to your frontend origin. Run Alembic migrations before production startup. Local SQLite tables are created on startup.

## Account behavior

- New Google users get a normal USER account, with no admin privileges.
- Subsequent sign-ins use Google's stable subject identifier, not an email match.
- Existing password accounts with the same email are **not automatically linked**. Use the original password for those accounts. Explicit account linking is not implemented.
- The app requests only OpenID and email; it does not request Drive/Gmail access or store Google access/refresh tokens or Google passwords.
- Google tokens are exchanged on the backend; a verified email is required. The backend retrieves user information directly from Google's HTTPS userinfo endpoint with the exchanged access token.
- One-time, ten-minute state is bound to an HTTP-only SameSite=Lax browser cookie; PKCE binds the authorization code to the login attempt. Normal app sessions remain HTTP-only, SameSite=Strict and expire after twelve hours.
- Logout revokes app sessions; it does not log the user out of their Google account.

## Verification

Automated tests cover provider configuration, state mismatch/replay/expiration, cancellation, verified-email enforcement, account collision, persistent identity, logout, non-admin access and network errors. Provider responses in tests are mocked; a real Google account round-trip must be verified after credentials are configured.

Google documentation: https://developers.google.com/identity/protocols/oauth2/web-server
