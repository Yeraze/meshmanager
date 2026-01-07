import { useState } from 'react'
import { useAuthContext } from '../../contexts/AuthContext'
import ConfigExportImport from './ConfigExportImport'
import DisplaySettings from './DisplaySettings'
import SourcesSettings from './SourcesSettings'
import UserSettings from './UserSettings'

type SettingsTab = 'display' | 'sources' | 'user'

export default function SettingsPage() {
  const { isAdmin } = useAuthContext()
  const [activeTab, setActiveTab] = useState<SettingsTab>('display')

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
        {isAdmin && (
          <button
            className={`tab ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            Sources
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
            {isAdmin && <ConfigExportImport />}
          </>
        )}
        {activeTab === 'sources' && isAdmin && <SourcesSettings />}
        {activeTab === 'user' && <UserSettings />}
      </div>
    </div>
  )
}
