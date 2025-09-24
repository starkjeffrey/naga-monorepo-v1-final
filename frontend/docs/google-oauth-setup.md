# Google OAuth Setup Guide

This guide explains how to configure Google OAuth 2.0 authentication for the NAGA SIS frontend application.

## Overview

The application now uses Google OAuth 2.0 for authentication, specifically designed for @pucsr.edu.kh email addresses. This provides secure, single sign-on access using Google Workspace accounts.

## Prerequisites

- Google Workspace account with admin privileges (for domain restriction)
- Access to Google Cloud Console
- Backend API supporting Google OAuth authentication

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Name: "NAGA SIS - PUCSR" (or similar)
4. Organization: Your institution's organization

## Step 2: Enable Google APIs

1. Navigate to **APIs & Services** → **Library**
2. Enable the following APIs:
   - **Google+ API** (for user profile information)
   - **Google OAuth2 API**
   - **People API** (optional, for extended profile data)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **Internal** (for Google Workspace users only)
3. Fill in required information:
   - **App name**: "NAGA Student Information System"
   - **User support email**: Your IT support email
   - **App logo**: Upload PUCSR/NAGA logo (optional)
   - **App domain**: Your application domain
   - **Developer contact**: Your development team email

4. **Scopes**: Add the following scopes:
   - `openid`
   - `email`
   - `profile`

5. **Test users**: Add test email addresses (if needed)

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Configure:
   - **Name**: "NAGA Frontend Web Client"
   - **Authorized JavaScript origins**:
     - `http://localhost:5173` (development)
     - `https://yourdomain.com` (production)
   - **Authorized redirect URIs**:
     - `http://localhost:5173/auth/callback` (development)
     - `https://yourdomain.com/auth/callback` (production)

5. Save and copy the **Client ID** (you'll need this for environment variables)

## Step 5: Configure Domain Restriction (Recommended)

To restrict authentication to @pucsr.edu.kh emails only:

1. In OAuth consent screen, ensure **Internal** is selected
2. The application code automatically validates the email domain
3. Google Workspace admin can set additional restrictions if needed

## Step 6: Environment Configuration

1. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

2. Update `.env.local` with your values:
   ```bash
   # Google OAuth Configuration
   VITE_GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
   VITE_GOOGLE_REDIRECT_URI=http://localhost:5173/auth/callback
   VITE_ALLOWED_EMAIL_DOMAIN=pucsr.edu.kh
   ```

3. For production, update the redirect URI to your production domain

## Step 7: Backend Configuration

Ensure your Django backend supports Google OAuth authentication:

1. **API Endpoint**: `POST /api/auth/google`
2. **Expected payload**:
   ```json
   {
     "google_token": "id_token_from_google",
     "access_token": "access_token_from_google",
     "email": "user@pucsr.edu.kh",
     "name": "User Name",
     "picture": "profile_image_url",
     "given_name": "First",
     "family_name": "Last",
     "domain": "pucsr.edu.kh"
   }
   ```

3. **Expected response**:
   ```json
   {
     "success": true,
     "jwt_token": "backend_jwt_token",
     "user_uuid": "user_uuid",
     "email": "user@pucsr.edu.kh",
     "role": "student|teacher",
     "expires_at": 1234567890,
     "profile": {
       "user_uuid": "uuid",
       "email": "user@pucsr.edu.kh",
       "full_name": "User Name",
       "role": "student",
       "status": "active"
     }
   }
   ```

## Step 8: Testing

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Navigate to `http://localhost:5173/signin`

3. Click "Sign in with Google Workspace"

4. Test with @pucsr.edu.kh email address

5. Verify:
   - Domain restriction works (non-@pucsr.edu.kh emails rejected)
   - Successful authentication redirects to dashboard
   - User profile and role are set correctly
   - JWT token is stored and used for API requests

## Security Considerations

1. **Domain Restriction**: Only @pucsr.edu.kh emails can authenticate
2. **HTTPS Required**: Use HTTPS in production
3. **JWT Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)
4. **Token Validation**: Backend validates Google tokens
5. **Session Management**: Tokens expire and require re-authentication

## Troubleshooting

### Common Issues

1. **"Invalid client_id"**
   - Check VITE_GOOGLE_CLIENT_ID is correct
   - Ensure client ID is for web application type

2. **"Unauthorized redirect_uri"**
   - Verify redirect URI is added to Google Console
   - Check exact URL match (including protocol)

3. **"Email domain not allowed"**
   - Ensure user has @pucsr.edu.kh email
   - Check VITE_ALLOWED_EMAIL_DOMAIN setting

4. **Backend authentication fails**
   - Verify backend API endpoint is correct
   - Check API base URL in environment
   - Ensure backend handles Google OAuth tokens

### Debug Mode

Enable debug logging by adding to environment:
```bash
VITE_ENABLE_DEV_TOOLS=true
```

This will show additional console logs for authentication flow debugging.

## Production Deployment

1. **Update redirect URIs** in Google Console for production domain
2. **Use HTTPS** for all production URLs
3. **Set production environment variables**
4. **Test authentication flow** thoroughly
5. **Monitor authentication errors** and usage

## Support

For technical support with Google OAuth setup:
- Check Google Cloud Console audit logs
- Review browser developer console for errors
- Verify backend API responses
- Test with different @pucsr.edu.kh accounts