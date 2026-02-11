# SSO (OpenID Connect)

MeshManager supports Single Sign-On (SSO) via OpenID Connect (OIDC). This allows users to authenticate using an external identity provider such as Authentik, Keycloak, Auth0, Okta, or Azure AD.

## Overview

When OIDC is configured, a **Sign in with SSO** button appears on the login page. Users click it to be redirected to your identity provider, authenticate there, and are redirected back to MeshManager with an active session.

Key features:
- **Auto-create users** on first SSO login (configurable)
- **First user becomes admin** automatically
- **Disable local auth** to enforce SSO-only access
- Works alongside local username/password authentication (unless disabled)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OIDC_ISSUER` | Yes | | OIDC provider issuer URL (see [Finding Your Issuer URL](#finding-your-issuer-url)) |
| `OIDC_CLIENT_ID` | Yes | | OAuth client ID from your provider |
| `OIDC_CLIENT_SECRET` | Yes | | OAuth client secret from your provider |
| `OIDC_REDIRECT_URI` | No | auto-detected | Callback URL (see [Redirect URI](#redirect-uri)) |
| `OIDC_SCOPES` | No | `openid email profile` | Space-separated OIDC scopes to request |
| `OIDC_AUTO_CREATE_USERS` | No | `true` | Auto-create user accounts on first SSO login |
| `DISABLE_LOCAL_AUTH` | No | `false` | Hide local login form and block password-based authentication |

OIDC is enabled automatically when `OIDC_ISSUER`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` are all set.

## Setup Guide

### 1. Create an Application in Your Identity Provider

In your OIDC provider, create a new application/client with the following settings:

- **Application type**: Web application
- **Grant type**: Authorization Code
- **Scopes**: `openid`, `email`, `profile`
- **Redirect URI**: `https://your-meshmanager-domain.com/auth/oidc/callback`

### 2. Configure MeshManager

Add the OIDC environment variables to your Docker Compose file:

```yaml
services:
  meshmanager:
    environment:
      OIDC_ISSUER: https://auth.example.com/application/o/meshmanager
      OIDC_CLIENT_ID: your-client-id
      OIDC_CLIENT_SECRET: your-client-secret
      OIDC_REDIRECT_URI: https://meshmanager.example.com/auth/oidc/callback
```

### 3. Restart MeshManager

```bash
docker compose up -d
```

The login page should now show a **Sign in with SSO** button.

## Redirect URI

The redirect URI tells your identity provider where to send users after authentication. It must match exactly in both your provider configuration and MeshManager.

The format is:
```
https://your-domain.com/auth/oidc/callback
```

If `OIDC_REDIRECT_URI` is not set, MeshManager will attempt to auto-detect it from the incoming request. However, this may not work correctly behind reverse proxies, so it's recommended to set it explicitly.

::: warning
The redirect URI must use the **public-facing URL** of your MeshManager instance, not an internal address. If you access MeshManager at `https://meshmanager.example.com`, the redirect URI should be `https://meshmanager.example.com/auth/oidc/callback`.
:::

## Finding Your Issuer URL

The issuer URL varies by provider. It must point to the base path where the provider serves its OpenID configuration.

MeshManager fetches `{OIDC_ISSUER}/.well-known/openid-configuration` to discover endpoints, so you can verify your issuer URL by visiting that address in a browser — it should return a JSON document.

### Common Providers

| Provider | Issuer URL Format |
|----------|-------------------|
| **Authentik** | `https://auth.example.com/application/o/<application-slug>` |
| **Keycloak** | `https://auth.example.com/realms/<realm-name>` |
| **Auth0** | `https://<tenant>.auth0.com` |
| **Okta** | `https://<org>.okta.com` |
| **Azure AD** | `https://login.microsoftonline.com/<tenant-id>/v2.0` |
| **Google** | `https://accounts.google.com` |

::: tip
You can verify your issuer URL by opening `{OIDC_ISSUER}/.well-known/openid-configuration` in a browser. It should return a JSON document with fields like `authorization_endpoint`, `token_endpoint`, etc.
:::

## Disabling Local Authentication

Set `DISABLE_LOCAL_AUTH=true` to enforce SSO-only login. When enabled:

- The username/password login form is hidden
- The `/auth/login` and `/auth/register` API endpoints return `403 Forbidden`
- Only the **Sign in with SSO** button is shown on the login page
- **First-user setup is not affected** — if no users exist, MeshManager will still show the registration form so you can create an initial admin account before enabling SSO

```yaml
services:
  meshmanager:
    environment:
      OIDC_ISSUER: https://auth.example.com/application/o/meshmanager
      OIDC_CLIENT_ID: your-client-id
      OIDC_CLIENT_SECRET: your-client-secret
      OIDC_REDIRECT_URI: https://meshmanager.example.com/auth/oidc/callback
      DISABLE_LOCAL_AUTH: "true"
```

::: danger
Do not enable `DISABLE_LOCAL_AUTH` without first confirming that OIDC login works correctly. If both local auth is disabled and OIDC is misconfigured, you will be locked out of the admin interface.
:::

## Auto-Create Users

By default (`OIDC_AUTO_CREATE_USERS=true`), MeshManager automatically creates a user account when someone logs in via SSO for the first time. The user's email and display name are populated from the OIDC token claims.

- The **first user** created (whether via SSO or local registration) is automatically granted the **admin** role
- Subsequent SSO users are created with the **user** role

To disable auto-creation (only allow SSO login for users that already exist):

```yaml
OIDC_AUTO_CREATE_USERS: "false"
```

When auto-creation is disabled, users who haven't been pre-created will see an error when attempting to log in via SSO.

## Provider-Specific Guides

### Authentik

1. In Authentik, go to **Applications > Providers** and create a new **OAuth2/OpenID Provider**
2. Set the **Redirect URI** to `https://your-domain.com/auth/oidc/callback`
3. Note the **Client ID** and **Client Secret**
4. Go to **Applications** and create a new application, linking it to the provider
5. The **Issuer URL** is `https://your-authentik-domain/application/o/<application-slug>`

::: tip
Make sure the application slug in the issuer URL matches the slug shown in Authentik's application settings, not the provider name.
:::

### Keycloak

1. In Keycloak, create a new **Client** in your realm
2. Set **Client Protocol** to `openid-connect`
3. Set **Access Type** to `confidential`
4. Add the redirect URI under **Valid Redirect URIs**
5. The **Issuer URL** is `https://your-keycloak-domain/realms/<realm-name>`

### Auth0

1. In Auth0, create a new **Regular Web Application**
2. Under **Settings**, note the **Domain**, **Client ID**, and **Client Secret**
3. Add the redirect URI under **Allowed Callback URLs**
4. The **Issuer URL** is `https://<your-tenant>.auth0.com`

## Troubleshooting

### "Internal Server Error" when clicking SSO

This usually means MeshManager cannot reach or parse your OIDC provider's discovery document. Check:

1. **Issuer URL is correct** — Verify `{OIDC_ISSUER}/.well-known/openid-configuration` returns valid JSON
2. **No trailing slash** — The issuer URL must not end with `/` (this causes a double-slash in the discovery URL, which many providers reject)
3. **Network connectivity** — The MeshManager container must be able to reach your OIDC provider. Check with:
   ```bash
   docker compose exec meshmanager curl -s https://your-issuer-url/.well-known/openid-configuration
   ```
4. **Check backend logs** for the specific error:
   ```bash
   docker compose logs meshmanager | tail -50
   ```

### "Redirect URI mismatch" error from provider

The redirect URI configured in your OIDC provider must exactly match the `OIDC_REDIRECT_URI` in MeshManager. Common mismatches:

- HTTP vs HTTPS (`http://` vs `https://`)
- Trailing slash (`/callback` vs `/callback/`)
- Port number differences
- Different domain or subdomain

### SSO login succeeds but user has no permissions

By default, SSO users are created with the **user** role. An admin can adjust roles and permissions on the [Settings > Users](/configuration/users) page.

### "Auto-creation of OIDC users is disabled" error

This means `OIDC_AUTO_CREATE_USERS` is set to `false` and the user logging in does not have a pre-existing account in MeshManager. Either:

- Set `OIDC_AUTO_CREATE_USERS=true`, or
- Create the user account in MeshManager's admin panel before they attempt SSO login

### "Local authentication is disabled" error

This message appears when `DISABLE_LOCAL_AUTH=true` and someone attempts to use the `/auth/login` or `/auth/register` API endpoints. This is expected behavior — users should authenticate via SSO instead.

### Session issues behind a reverse proxy

If SSO login redirects succeed but the session is not preserved, check:

- Your reverse proxy is forwarding the `Cookie` header
- The `Host` header matches the public domain
- If using HTTPS, ensure the proxy sets `X-Forwarded-Proto: https`

## Full Example

A complete Docker Compose configuration with OIDC and local auth disabled:

```yaml
services:
  meshmanager:
    image: ghcr.io/yeraze/meshmanager:latest
    ports:
      - "8080:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://meshmanager:secure_password@postgres/meshmanager
      SESSION_SECRET: generate-a-long-random-string-here

      # OIDC Configuration
      OIDC_ISSUER: https://auth.example.com/application/o/meshmanager
      OIDC_CLIENT_ID: your-client-id
      OIDC_CLIENT_SECRET: your-client-secret
      OIDC_REDIRECT_URI: https://meshmanager.example.com/auth/oidc/callback
      OIDC_SCOPES: openid email profile
      OIDC_AUTO_CREATE_USERS: "true"

      # Disable local login (SSO only)
      DISABLE_LOCAL_AUTH: "true"
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: meshmanager
      POSTGRES_USER: meshmanager
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U meshmanager"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```
