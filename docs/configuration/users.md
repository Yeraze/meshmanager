# User Management & Permissions

MeshManager includes a built-in authentication and authorization system. The first user to register automatically becomes an admin. All users and permissions are managed through the **Settings > Users** page.

## User Roles

MeshManager has two roles:

| Role | Description |
|------|-------------|
| **Admin** | Full access to all features. Can manage users, data sources, and system settings. Bypasses all tab-based permissions. |
| **User** | Access governed by per-tab permissions. Cannot access the Settings page (user management, sources, etc.) unless explicitly granted. |

## Tab-Based Permissions

Each user (except admins, who always have full access) has read and write permissions for each of the six application tabs:

| Tab | Controls |
|-----|----------|
| **Map** | Interactive map with node positions and heatmaps |
| **Nodes** | Node list, filtering, and node detail views |
| **Graphs** | Telemetry charts (battery, channel utilization, signal quality, etc.) |
| **Analysis** | Traceroute visualization, network topology, and signal analysis |
| **Communication** | Messages and communication data |
| **Settings** | User management, data sources, solar config, and notifications |

Each tab has two permission flags:

- **Read** — Can view the tab and its data
- **Write** — Can make changes (e.g., edit node names, trigger actions)

When a tab's read permission is disabled, the tab is hidden from the user's navigation.

## Managing Users

Admins can manage users at **Settings > Users**:

- **Create** — Add new users with a username, password, and optional email/display name. Set their role and permissions.
- **Edit** — Change a user's role, permissions, active status, or reset their password.
- **Delete** — Remove a user account.

### Two-Factor Authentication (TOTP)

Users can enable TOTP-based two-factor authentication from their profile. When enabled, a six-digit code from an authenticator app (Google Authenticator, Authy, etc.) is required at each login.

## Anonymous User (Public Access)

MeshManager includes a built-in **anonymous user** that controls what unauthenticated visitors can see. This allows you to make parts of your dashboard publicly accessible without requiring login.

Key characteristics:

- **Always present** — The anonymous user appears at the top of the Users list with an "Anonymous" badge. It cannot be deleted.
- **Permissions only** — Only the anonymous user's tab permissions can be edited. Username, password, and role cannot be changed.
- **Default behavior** — Read access is enabled for all tabs except Settings, with write access disabled everywhere. This preserves open, read-only behavior for existing deployments.
- **Restricting access** — To hide a tab from unauthenticated visitors, disable its read permission on the anonymous user.
- **Login prompt** — When an unauthenticated visitor tries to access a tab the anonymous user cannot read, they receive a 401 response which triggers the login modal.

## Default Permissions

| Tab | Admin | Regular User | Anonymous |
|-----|-------|-------------|-----------|
| Map | read + write | read | read |
| Nodes | read + write | read | read |
| Graphs | read + write | read | read |
| Analysis | read + write | read | read |
| Communication | read + write | read | read |
| Settings | read + write | read | no access |

::: tip
Admin users bypass the permissions system entirely — they always have full read and write access regardless of what their permissions dict contains.
:::

## Examples

### Make the dashboard fully private

Set all anonymous user tab permissions to no read access. Every visitor will be prompted to log in.

### Allow public map but require login for everything else

On the anonymous user, enable read for the **Map** tab only. Disable read on all other tabs.

### Create a read-only monitoring user

Create a regular user with read enabled on all tabs and write disabled everywhere. This user can view all data but cannot make any changes.
