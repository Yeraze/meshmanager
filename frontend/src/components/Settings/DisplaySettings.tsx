import { useDataContext } from '../../contexts/DataContext'

const PRESET_HOURS = [1, 6, 12, 24, 48, 72, 168, 720]
const ONLINE_PRESET_HOURS = [1, 2, 4, 6, 12, 24]

export default function DisplaySettings() {
  const { activeHours, setActiveHours, onlineHours, setOnlineHours } = useDataContext()

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2>Display Settings</h2>
      </div>

      <div className="settings-card">
        <h3>Active Node Threshold</h3>
        <p className="settings-description">
          Nodes that haven't been heard from within this time period will be hidden when "Active only" is enabled.
        </p>

        <div className="form-group">
          <label className="form-label">Consider nodes active if heard within:</label>
          <div className="active-hours-selector">
            {PRESET_HOURS.map((hours) => (
              <button
                key={hours}
                className={`active-hours-button ${activeHours === hours ? 'active' : ''}`}
                onClick={() => setActiveHours(hours)}
              >
                {formatHours(hours)}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Or enter custom hours (1-8760):</label>
          <div className="custom-hours-input">
            <input
              type="number"
              className="form-input"
              min={1}
              max={8760}
              value={activeHours}
              onChange={(e) => {
                const value = parseInt(e.target.value, 10)
                if (!isNaN(value) && value >= 1 && value <= 8760) {
                  setActiveHours(value)
                }
              }}
            />
            <span className="hours-label">hours</span>
          </div>
        </div>

        <p className="settings-hint">
          Current setting: Nodes are considered active if heard within the last {formatHours(activeHours)}.
        </p>
      </div>

      <div className="settings-card">
        <h3>Online Status Threshold</h3>
        <p className="settings-description">
          Nodes that haven't been heard from within this time period will be shown as "Offline" in the UI.
        </p>

        <div className="form-group">
          <label className="form-label">Consider nodes online if heard within:</label>
          <div className="active-hours-selector">
            {ONLINE_PRESET_HOURS.map((hours) => (
              <button
                key={hours}
                className={`active-hours-button ${onlineHours === hours ? 'active' : ''}`}
                onClick={() => setOnlineHours(hours)}
              >
                {formatHours(hours)}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Or enter custom hours (1-168):</label>
          <div className="custom-hours-input">
            <input
              type="number"
              className="form-input"
              min={1}
              max={168}
              value={onlineHours}
              onChange={(e) => {
                const value = parseInt(e.target.value, 10)
                if (!isNaN(value) && value >= 1 && value <= 168) {
                  setOnlineHours(value)
                }
              }}
            />
            <span className="hours-label">hours</span>
          </div>
        </div>

        <p className="settings-hint">
          Current setting: Nodes are considered online if heard within the last {formatHours(onlineHours)}.
        </p>
      </div>
    </div>
  )
}

function formatHours(hours: number): string {
  if (hours < 24) {
    return `${hours}h`
  } else if (hours < 168) {
    const days = hours / 24
    return `${days}d`
  } else if (hours < 720) {
    const weeks = hours / 168
    return `${weeks}w`
  } else {
    const months = hours / 720
    return `${months}mo`
  }
}
