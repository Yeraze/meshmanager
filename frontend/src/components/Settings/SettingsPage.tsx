import { useState } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import ConfigExportImport from './ConfigExportImport'
import RetentionSettings from './RetentionSettings'
import DisplaySettings from './DisplaySettings'
import SourcesSettings from './SourcesSettings'
import UsersManagement from './UsersManagement'
import UserSettings from './UserSettings'

type SettingsTab = 'display' | 'sources' | 'users' | 'user'

export default function SettingsPage() {
  const { isAdmin, hasPermission } = useAuthContext()
  const [activeTab, setActiveTab] = useState<SettingsTab>('display')
  const canWriteSettings = hasPermission('settings', 'write')

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'display' ? 'active' : ''}`}
          onClick={() => setActiveTab('display')}
        >
          Display
        </button>
        {canWriteSettings && (
          <button
            className={`tab ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            Sources
          </button>
        )}
        {isAdmin && (
          <button
            className={`tab ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
        )}
        <button
          className={`tab ${activeTab === 'user' ? 'active' : ''}`}
          onClick={() => setActiveTab('user')}
        >
          User
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'display' && (
          <>
            <DisplaySettings />
            {canWriteSettings && <RetentionSettings />}
            {canWriteSettings && <ConfigExportImport />}
          </>
        )}
        {activeTab === 'sources' && canWriteSettings && <SourcesSettings />}
        {activeTab === 'users' && isAdmin && <UsersManagement />}
        {activeTab === 'user' && <UserSettings />}
      </div>
    </div>
  )
}
