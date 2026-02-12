import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { MapContainer as LeafletMapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useNodes } from '../../hooks/useNodes'
import { getTilesetById, DEFAULT_TILESET_ID } from '../../config/tilesets'
import type { MessageSourceDetail } from '../../services/api'
import styles from './PropagationMapModal.module.css'

interface PropagationMapModalProps {
  sources: MessageSourceDetail[]
  onClose: () => void
}

interface GatewayEvent {
  gatewayNodeNum: number
  name: string
  lat: number
  lng: number
  timestamp: number
  relativeTimeMs: number
  order: number
  sourceName: string
  rxSnr: number | null
}

function getOrderColor(order: number, total: number): string {
  if (total <= 1) return '#a6e3a1'
  const ratio = order / (total - 1)
  // green -> yellow -> red
  if (ratio <= 0.5) {
    const t = ratio * 2
    const r = Math.round(166 + (249 - 166) * t)
    const g = Math.round(227 + (226 - 227) * t)
    const b = Math.round(161 + (175 - 161) * t)
    return `rgb(${r},${g},${b})`
  } else {
    const t = (ratio - 0.5) * 2
    const r = Math.round(249 + (243 - 249) * t)
    const g = Math.round(226 + (139 - 226) * t)
    const b = Math.round(175 + (168 - 175) * t)
    return `rgb(${r},${g},${b})`
  }
}

function createGatewayIcon(state: 'inactive' | 'active' | 'pulsing', color: string): L.DivIcon {
  let className = styles.gatewayMarker
  let style = ''

  if (state === 'inactive') {
    className += ' ' + styles.gatewayMarkerInactive
  } else if (state === 'active') {
    className += ' ' + styles.gatewayMarkerActive
    style = `background: ${color};`
  } else {
    className += ' ' + styles.gatewayMarkerPulsing
    style = `background: ${color}; box-shadow: 0 0 8px ${color};`
  }

  return L.divIcon({
    className: '',
    html: `<div class="${className}" style="width:18px;height:18px;${style}"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function FitBoundsHandler({ positions }: { positions: [number, number][] }) {
  const map = useMap()

  useEffect(() => {
    if (positions.length === 0) return
    if (positions.length === 1) {
      map.setView(positions[0], 12)
      return
    }
    const bounds = L.latLngBounds(positions.map(p => L.latLng(p[0], p[1])))
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
  }, [map, positions])

  return null
}

function formatRelativeTime(ms: number): string {
  if (ms < 1000) return `+${ms}ms`
  if (ms < 60000) return `+${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `+${mins}m ${secs}s`
}

export default function PropagationMapModal({ sources, onClose }: PropagationMapModalProps) {
  const { data: nodes } = useNodes()
  const [currentStep, setCurrentStep] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const gatewayEvents = useMemo<GatewayEvent[]>(() => {
    if (!nodes || nodes.length === 0) return []

    const nodeMap = new Map<number, { lat: number; lng: number; name: string }>()
    for (const node of nodes) {
      if (node.latitude !== null && node.longitude !== null) {
        nodeMap.set(node.node_num, {
          lat: node.latitude,
          lng: node.longitude,
          name: node.short_name || `!${node.node_num.toString(16).padStart(8, '0')}`,
        })
      }
    }

    // Group by gateway_node_num, keep earliest timestamp per gateway
    const byGateway = new Map<number, { source: MessageSourceDetail; ts: number }>()
    for (const s of sources) {
      if (!s.gateway_node_num) continue
      const nodeInfo = nodeMap.get(s.gateway_node_num)
      if (!nodeInfo) continue

      const tsStr = s.rx_time || s.received_at
      const ts = new Date(tsStr).getTime()
      if (isNaN(ts)) continue

      const existing = byGateway.get(s.gateway_node_num)
      if (!existing || ts < existing.ts) {
        byGateway.set(s.gateway_node_num, { source: s, ts })
      }
    }

    const sorted = Array.from(byGateway.entries())
      .sort((a, b) => a[1].ts - b[1].ts)

    if (sorted.length === 0) return []

    const earliest = sorted[0][1].ts
    return sorted.map(([nodeNum, { source, ts }], idx) => {
      const nodeInfo = nodeMap.get(nodeNum)!
      return {
        gatewayNodeNum: nodeNum,
        name: nodeInfo.name,
        lat: nodeInfo.lat,
        lng: nodeInfo.lng,
        timestamp: ts,
        relativeTimeMs: ts - earliest,
        order: idx,
        sourceName: source.source_name,
        rxSnr: source.rx_snr,
      }
    })
  }, [sources, nodes])

  const totalGateways = new Set(sources.map(s => s.gateway_node_num).filter(Boolean)).size
  const positionedCount = gatewayEvents.length

  const positions = useMemo<[number, number][]>(
    () => gatewayEvents.map(e => [e.lat, e.lng]),
    [gatewayEvents]
  )

  // Animation engine
  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!isPlaying || gatewayEvents.length < 2) return

    const nextStep = currentStep + 1
    if (nextStep >= gatewayEvents.length) {
      setIsPlaying(false)
      return
    }

    // Compute delay proportional to real time deltas, scaled to ~4s total
    const totalSpan = gatewayEvents[gatewayEvents.length - 1].relativeTimeMs
    let delay: number
    if (totalSpan === 0 || currentStep < 0) {
      delay = 500
    } else {
      const delta = gatewayEvents[nextStep].relativeTimeMs - gatewayEvents[Math.max(0, currentStep)].relativeTimeMs
      const scaleFactor = totalSpan > 0 ? 4000 / totalSpan : 1
      delay = Math.min(2000, Math.max(300, delta * scaleFactor))
    }

    timerRef.current = setTimeout(() => {
      setCurrentStep(nextStep)
    }, delay)

    return clearTimer
  }, [isPlaying, currentStep, gatewayEvents, clearTimer])

  useEffect(() => {
    return clearTimer
  }, [clearTimer])

  const handlePlay = () => {
    if (currentStep >= gatewayEvents.length - 1) {
      setCurrentStep(-1)
    }
    setIsPlaying(true)
    if (currentStep < 0) {
      setCurrentStep(0)
    }
  }

  const handlePause = () => {
    setIsPlaying(false)
    clearTimer()
  }

  const handleRestart = () => {
    setIsPlaying(false)
    clearTimer()
    setCurrentStep(-1)
  }

  const handleStepForward = () => {
    setIsPlaying(false)
    clearTimer()
    const next = currentStep + 1
    if (next < gatewayEvents.length) {
      setCurrentStep(next)
    }
  }

  const handleJumpTo = (step: number) => {
    setIsPlaying(false)
    clearTimer()
    setCurrentStep(step)
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  const tileset = getTilesetById(DEFAULT_TILESET_ID)

  // Build status label
  let statusText = ''
  if (gatewayEvents.length > 0 && currentStep >= 0) {
    const evt = gatewayEvents[currentStep]
    const timeStr = evt.relativeTimeMs > 0 ? ` (${formatRelativeTime(evt.relativeTimeMs)})` : ''
    statusText = `${currentStep + 1}/${gatewayEvents.length} — ${evt.name}${timeStr}`
  } else if (gatewayEvents.length > 0) {
    statusText = `0/${gatewayEvents.length} — Ready`
  }

  if (positionedCount === 0) {
    return (
      <div className={styles.overlay} onClick={handleOverlayClick}>
        <div className={styles.modal} style={{ height: 'auto', maxHeight: '40vh' }}>
          <div className={styles.header}>
            <h3 className={styles.title}>Propagation Map</h3>
            <button className={styles.closeButton} onClick={onClose} title="Close">&times;</button>
          </div>
          <div className={styles.noDataMessage}>
            No gateways with known positions found.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.overlay} onClick={handleOverlayClick}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h3 className={styles.title}>Propagation Map</h3>
          <button className={styles.closeButton} onClick={onClose} title="Close">&times;</button>
        </div>

        {positionedCount < totalGateways && (
          <div className={styles.positionWarning}>
            {positionedCount} of {totalGateways} gateways have known positions
          </div>
        )}

        <div className={styles.mapContainer}>
          <LeafletMapContainer
            center={positions[0] || [0, 0]}
            zoom={10}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution={tileset.attribution}
              url={tileset.url}
              maxZoom={tileset.maxZoom}
            />
            <FitBoundsHandler positions={positions} />

            {gatewayEvents.map((evt) => {
              let state: 'inactive' | 'active' | 'pulsing' = 'inactive'
              if (currentStep >= 0) {
                if (evt.order < currentStep) state = 'active'
                else if (evt.order === currentStep) state = 'pulsing'
              }

              const color = getOrderColor(evt.order, gatewayEvents.length)
              const icon = createGatewayIcon(state, color)

              return (
                <Marker
                  key={evt.gatewayNodeNum}
                  position={[evt.lat, evt.lng]}
                  icon={icon}
                >
                  <Tooltip direction="top" offset={[0, -14]}>
                    <strong>{evt.name}</strong><br />
                    {evt.sourceName}
                    {evt.rxSnr !== null && <><br />SNR: {evt.rxSnr.toFixed(1)} dB</>}
                    {evt.relativeTimeMs > 0 && <><br />{formatRelativeTime(evt.relativeTimeMs)}</>}
                  </Tooltip>
                </Marker>
              )
            })}
          </LeafletMapContainer>
        </div>

        {gatewayEvents.length >= 2 && (
          <div className={styles.controls}>
            <button
              className={styles.controlButton}
              onClick={isPlaying ? handlePause : handlePlay}
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? '\u23F8' : '\u25B6'}
            </button>
            <button
              className={styles.controlButton}
              onClick={handleRestart}
              title="Restart"
            >
              \u23EE
            </button>
            <button
              className={styles.controlButton}
              onClick={handleStepForward}
              title="Step Forward"
              disabled={currentStep >= gatewayEvents.length - 1}
            >
              \u23ED
            </button>

            <div className={styles.timeline}>
              <div className={styles.timelineTrack} />
              <div
                className={styles.timelineFill}
                style={{
                  width: currentStep >= 0
                    ? `${((currentStep + 1) / gatewayEvents.length) * 100}%`
                    : '0%',
                }}
              />
              {gatewayEvents.map((evt) => {
                const totalSpan = gatewayEvents[gatewayEvents.length - 1].relativeTimeMs
                const pct = totalSpan > 0
                  ? (evt.relativeTimeMs / totalSpan) * 100
                  : (evt.order / (gatewayEvents.length - 1)) * 100

                let dotClass = styles.timelineDot
                if (currentStep >= 0 && evt.order === currentStep) {
                  dotClass += ' ' + styles.timelineDotCurrent
                } else if (currentStep >= 0 && evt.order < currentStep) {
                  dotClass += ' ' + styles.timelineDotActive
                }

                return (
                  <div
                    key={evt.gatewayNodeNum}
                    className={dotClass}
                    style={{ left: `${pct}%` }}
                    onClick={() => handleJumpTo(evt.order)}
                    title={`${evt.name}${evt.relativeTimeMs > 0 ? ' ' + formatRelativeTime(evt.relativeTimeMs) : ''}`}
                  />
                )
              })}
            </div>

            <span className={styles.statusLabel}>{statusText}</span>
          </div>
        )}
      </div>
    </div>
  )
}
