# Environment Variables

MeshManager is configured primarily through environment variables. These can be set in a `.env` file or passed directly to Docker.

## Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://meshmanager:meshmanager@postgres:5432/meshmanager` | PostgreSQL connection string |
| `POSTGRES_USER` | `meshmanager` | Database username |
| `POSTGRES_PASSWORD` | `meshmanager` | Database password |
| `POSTGRES_DB` | `meshmanager` | Database name |

::: warning
Change the default database credentials in production environments.
:::

## Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `SESSION_SECRET` | (required) | Secret key for session encryption |

## Authentication

Authentication is always enabled. The first user to register becomes an admin.

For SSO configuration details, see the [SSO (OpenID Connect)](/configuration/sso) guide.

::: tip
Anonymous user permissions and per-user tab permissions are configured through the web UI at **Settings > Users**, not via environment variables. See the [User Management](/configuration/users) guide for details.
:::

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_ISSUER` | | OIDC provider issuer URL |
| `OIDC_CLIENT_ID` | | OIDC client ID |
| `OIDC_CLIENT_SECRET` | | OIDC client secret |
| `OIDC_REDIRECT_URI` | auto-detected | OIDC callback URL |
| `OIDC_SCOPES` | `openid email profile` | Space-separated OIDC scopes to request |
| `OIDC_AUTO_CREATE_USERS` | `true` | Auto-create users on first SSO login |
| `DISABLE_LOCAL_AUTH` | `false` | Disable local username/password login |

## Data Collection

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTION_INTERVAL` | `300` | Seconds between data collection cycles |
| `CATCHUP_HOURS` | `24` | Hours of historical data to collect on startup |

## Example .env File

```bash
# Database
DATABASE_URL=postgresql+asyncpg://meshmanager:secure_password@postgres/meshmanager
POSTGRES_PASSWORD=secure_password

# Application
LOG_LEVEL=INFO
SESSION_SECRET=your-secure-random-string-here

# OIDC Authentication (optional)
OIDC_ISSUER=https://auth.example.com/application/o/meshmanager
OIDC_CLIENT_ID=meshmanager
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://meshmanager.example.com/auth/oidc/callback
# OIDC_SCOPES=openid email profile
# OIDC_AUTO_CREATE_USERS=true
# DISABLE_LOCAL_AUTH=false
```

## Security Best Practices

1. **Always change default passwords** - Never use the default `meshmanager` password in production
2. **Use a strong SESSION_SECRET** - Generate a random string of at least 32 characters
3. **Enable authentication** - Protect the admin interface in public deployments
4. **Use HTTPS** - Configure a reverse proxy with TLS certificates
5. **Restrict CORS** - Set specific origins instead of `*` in production
