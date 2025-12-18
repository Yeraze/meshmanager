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

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_ENABLED` | `false` | Enable authentication |
| `OIDC_ENABLED` | `false` | Enable OpenID Connect |
| `OIDC_ISSUER` | | OIDC provider issuer URL |
| `OIDC_CLIENT_ID` | | OIDC client ID |
| `OIDC_CLIENT_SECRET` | | OIDC client secret |
| `OIDC_REDIRECT_URI` | | OIDC callback URL |

## Data Collection

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTION_INTERVAL` | `300` | Seconds between data collection cycles |
| `CATCHUP_HOURS` | `24` | Hours of historical data to collect on startup |

## Example .env File

```bash
# Database
DATABASE_URL=postgresql://meshmanager:secure_password@postgres:5432/meshmanager
POSTGRES_PASSWORD=secure_password

# Application
LOG_LEVEL=INFO
SESSION_SECRET=your-secure-random-string-here

# Authentication (optional)
AUTH_ENABLED=true
OIDC_ENABLED=true
OIDC_ISSUER=https://auth.example.com
OIDC_CLIENT_ID=meshmanager
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://meshmanager.example.com/api/auth/oidc/callback
```

## Security Best Practices

1. **Always change default passwords** - Never use the default `meshmanager` password in production
2. **Use a strong SESSION_SECRET** - Generate a random string of at least 32 characters
3. **Enable authentication** - Protect the admin interface in public deployments
4. **Use HTTPS** - Configure a reverse proxy with TLS certificates
5. **Restrict CORS** - Set specific origins instead of `*` in production
