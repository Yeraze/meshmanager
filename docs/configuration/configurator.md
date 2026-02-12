# Docker Compose Configurator

<script setup>
import { ref, computed } from 'vue'

const config = ref({
  port: '8080',
  sessionSecret: '',
  postgresPassword: 'meshmanager',
  version: 'latest',
  oidcEnabled: false,
  oidcIssuer: '',
  oidcClientId: '',
  oidcClientSecret: '',
  oidcRedirectUri: '',
  logLevel: 'INFO',
})

const generateSecret = () => {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  config.value.sessionSecret = Array.from(array, b => b.toString(16).padStart(2, '0')).join('')
}

const dockerCompose = computed(() => {
  let yaml = `services:
  postgres:
    image: postgres:16-alpine
    container_name: meshmanager-db
    environment:
      POSTGRES_DB: meshmanager
      POSTGRES_USER: meshmanager
      POSTGRES_PASSWORD: ${config.value.postgresPassword}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U meshmanager"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  meshmanager:
    image: ghcr.io/yeraze/meshmanager:${config.value.version}
    container_name: meshmanager
    ports:
      - "${config.value.port}:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://meshmanager:${config.value.postgresPassword}@postgres/meshmanager
      SESSION_SECRET: ${config.value.sessionSecret || 'GENERATE_ME'}
      LOG_LEVEL: ${config.value.logLevel}`

  if (config.value.oidcEnabled) {
    yaml += `
      OIDC_ISSUER: ${config.value.oidcIssuer}
      OIDC_CLIENT_ID: ${config.value.oidcClientId}
      OIDC_CLIENT_SECRET: ${config.value.oidcClientSecret}
      OIDC_REDIRECT_URI: ${config.value.oidcRedirectUri}`
  }

  yaml += `
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
`
  return yaml
})

const copyToClipboard = async () => {
  await navigator.clipboard.writeText(dockerCompose.value)
}
</script>

Use this interactive configurator to generate a customized `docker-compose.yml` for your MeshManager deployment.

## Configuration Options

<div class="configurator-form">

### Basic Settings

<div class="form-group">
  <label for="port">Web Interface Port</label>
  <input type="text" id="port" v-model="config.port" placeholder="8080" />
  <small>The port to access MeshManager on your host</small>
</div>

<div class="form-group">
  <label for="version">MeshManager Version</label>
  <select id="version" v-model="config.version">
    <option value="latest">latest (recommended)</option>
    <option value="0.7.0">0.7.0</option>
    <option value="0.6.7">0.6.7</option>
    <option value="0.6.6">0.6.6</option>
    <option value="0.6.5">0.6.5</option>
    <option value="0.6.4">0.6.4</option>
    <option value="0.6.3">0.6.3</option>
    <option value="0.6.2">0.6.2</option>
    <option value="0.6.1">0.6.1</option>
    <option value="0.6.0">0.6.0</option>
    <option value="0.5.2">0.5.2</option>
    <option value="0.5.0">0.5.0</option>
  </select>
</div>

<div class="form-group">
  <label for="logLevel">Log Level</label>
  <select id="logLevel" v-model="config.logLevel">
    <option value="DEBUG">DEBUG</option>
    <option value="INFO">INFO (default)</option>
    <option value="WARNING">WARNING</option>
    <option value="ERROR">ERROR</option>
  </select>
</div>

### Security Settings

<div class="form-group">
  <label for="sessionSecret">Session Secret</label>
  <div class="input-with-button">
    <input type="text" id="sessionSecret" v-model="config.sessionSecret" placeholder="Click Generate to create" />
    <button @click="generateSecret" class="generate-btn">Generate</button>
  </div>
  <small>Required: A random 64-character hex string for session encryption</small>
</div>

<div class="form-group">
  <label for="postgresPassword">PostgreSQL Password</label>
  <input type="text" id="postgresPassword" v-model="config.postgresPassword" placeholder="meshmanager" />
  <small>Database password (change from default in production)</small>
</div>

### OIDC Authentication (Optional)

<div class="form-group">
  <label class="checkbox-label">
    <input type="checkbox" v-model="config.oidcEnabled" />
    Enable OIDC/SSO Authentication
  </label>
</div>

<div v-if="config.oidcEnabled" class="oidc-settings">
  <div class="form-group">
    <label for="oidcIssuer">OIDC Issuer URL</label>
    <input type="text" id="oidcIssuer" v-model="config.oidcIssuer" placeholder="https://auth.example.com" />
  </div>
  <div class="form-group">
    <label for="oidcClientId">Client ID</label>
    <input type="text" id="oidcClientId" v-model="config.oidcClientId" placeholder="meshmanager" />
  </div>
  <div class="form-group">
    <label for="oidcClientSecret">Client Secret</label>
    <input type="password" id="oidcClientSecret" v-model="config.oidcClientSecret" />
  </div>
  <div class="form-group">
    <label for="oidcRedirectUri">Redirect URI</label>
    <input type="text" id="oidcRedirectUri" v-model="config.oidcRedirectUri" :placeholder="`http://localhost:${config.port}/auth/callback`" />
  </div>
</div>

</div>

## Generated Configuration

<div class="generated-config">
  <div class="config-header">
    <span>docker-compose.yml</span>
    <button @click="copyToClipboard" class="copy-btn">Copy</button>
  </div>
  <pre><code>{{ dockerCompose }}</code></pre>
</div>

## Next Steps

1. Save the configuration above as `docker-compose.yml`
2. Run `docker compose up -d` to start MeshManager
3. Access the web interface at `http://localhost:{{ config.port }}`
4. [Add your first data source](/getting-started#adding-your-first-data-source)

<style>
.configurator-form {
  background: var(--vp-c-bg-soft);
  padding: 1.5rem;
  border-radius: 8px;
  margin: 1rem 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.form-group input[type="text"],
.form-group input[type="password"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--vp-c-border);
  border-radius: 4px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 0.9rem;
}

.form-group small {
  display: block;
  color: var(--vp-c-text-2);
  margin-top: 0.25rem;
  font-size: 0.85rem;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input {
  width: auto !important;
}

.input-with-button {
  display: flex;
  gap: 0.5rem;
}

.input-with-button input {
  flex: 1;
}

.generate-btn, .copy-btn {
  padding: 0.5rem 1rem;
  background: var(--vp-c-brand-1);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.generate-btn:hover, .copy-btn:hover {
  background: var(--vp-c-brand-2);
}

.oidc-settings {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--vp-c-bg);
  border-radius: 4px;
  border: 1px solid var(--vp-c-border);
}

.generated-config {
  margin: 1rem 0;
  border: 1px solid var(--vp-c-border);
  border-radius: 8px;
  overflow: hidden;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--vp-c-bg-soft);
  border-bottom: 1px solid var(--vp-c-border);
  font-weight: 600;
}

.generated-config pre {
  margin: 0;
  padding: 1rem;
  background: var(--vp-c-bg);
  overflow-x: auto;
}

.generated-config code {
  font-family: var(--vp-font-family-mono);
  font-size: 0.85rem;
  line-height: 1.6;
}
</style>
