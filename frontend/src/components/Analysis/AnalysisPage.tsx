import { useState } from 'react'
import NetworkTopology from './NetworkTopology'

type AnalysisType = 'network-topology' | null

interface AnalysisCard {
  id: AnalysisType
  title: string
  description: string
  icon: string
}

const analyses: AnalysisCard[] = [
  {
    id: 'network-topology',
    title: 'Network Routing Topology',
    description: 'Analyze traceroute data to identify trunk lines (high-traffic routes) and clusters (hubs with many connections).',
    icon: '🔗',
  },
  // Future analyses can be added here
]

export default function AnalysisPage() {
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisType>(null)

  const renderAnalysis = () => {
    switch (selectedAnalysis) {
      case 'network-topology':
        return <NetworkTopology />
      default:
        return null
    }
  }

  // If an analysis is selected, show it in full view
  if (selectedAnalysis) {
    return (
      <div className="analysis-page" style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}>
        <div className="settings-header" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexShrink: 0,
        }}>
          <button
            onClick={() => setSelectedAnalysis(null)}
            style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: 'var(--color-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span style={{ fontSize: '1.2rem' }}>&larr;</span> Back
          </button>
          <h1 style={{ margin: 0 }}>
            {analyses.find(a => a.id === selectedAnalysis)?.title}
          </h1>
        </div>

        <div style={{
          padding: '1rem',
          flex: 1,
          overflow: 'auto',
          minHeight: 0,
        }}>
          {renderAnalysis()}
        </div>
      </div>
    )
  }

  // Show grid of analysis cards
  return (
    <div className="analysis-page">
      <div className="settings-header">
        <h1>Analysis</h1>
      </div>

      <div style={{
        padding: '1.5rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '1.5rem',
      }}>
        {analyses.map(analysis => (
          <button
            key={analysis.id}
            onClick={() => setSelectedAnalysis(analysis.id)}
            style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '8px',
              padding: '1.5rem',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--color-primary)'
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--color-border)'
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <div style={{ fontSize: '2.5rem' }}>{analysis.icon}</div>
            <div>
              <h3 style={{
                margin: 0,
                fontSize: '1.125rem',
                color: 'var(--color-text)',
                fontWeight: 600,
              }}>
                {analysis.title}
              </h3>
              <p style={{
                margin: '0.5rem 0 0',
                fontSize: '0.875rem',
                color: 'var(--color-text-muted)',
                lineHeight: 1.5,
              }}>
                {analysis.description}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
