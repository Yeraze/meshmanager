import { useState } from 'react'
import CoverageMapModal from './CoverageMapModal'

export default function GraphsPage() {
  const [showCoverageMap, setShowCoverageMap] = useState(false)

  return (
    <div className="graphs-page">
      <div className="settings-header">
        <h1>Graphs</h1>
      </div>

      <div className="graphs-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '1rem',
        padding: '1rem',
      }}>
        {/* Coverage Map Card */}
        <div
          className="graph-card"
          style={{
            background: 'var(--color-surface)',
            borderRadius: '8px',
            padding: '1.5rem',
            cursor: 'pointer',
            transition: 'transform 0.2s, box-shadow 0.2s',
            border: '1px solid var(--color-border)',
          }}
          onClick={() => setShowCoverageMap(true)}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🗺️</div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Coverage Map</h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            View a heatmap of position reports across the network over time.
          </p>
        </div>

        {/* Placeholder cards for future graphs */}
        <div
          className="graph-card"
          style={{
            background: 'var(--color-surface)',
            borderRadius: '8px',
            padding: '1.5rem',
            border: '1px solid var(--color-border)',
            opacity: 0.6,
          }}
        >
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>📈</div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Signal Strength</h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Coming soon: Track signal strength over time.
          </p>
        </div>

        <div
          className="graph-card"
          style={{
            background: 'var(--color-surface)',
            borderRadius: '8px',
            padding: '1.5rem',
            border: '1px solid var(--color-border)',
            opacity: 0.6,
          }}
        >
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔗</div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Node Connections</h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Coming soon: Visualize network topology.
          </p>
        </div>

        <div
          className="graph-card"
          style={{
            background: 'var(--color-surface)',
            borderRadius: '8px',
            padding: '1.5rem',
            border: '1px solid var(--color-border)',
            opacity: 0.6,
          }}
        >
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>💬</div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Message Activity</h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Coming soon: View message traffic patterns.
          </p>
        </div>
      </div>

      <CoverageMapModal
        isOpen={showCoverageMap}
        onClose={() => setShowCoverageMap(false)}
      />
    </div>
  )
}
