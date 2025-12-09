import { useState } from 'react'
import { getAllTilesets, getTilePreviewUrl, type TilesetId } from '../../config/tilesets'

interface TilesetSelectorProps {
  selectedTilesetId: TilesetId
  onTilesetChange: (tilesetId: TilesetId) => void
}

export default function TilesetSelector({ selectedTilesetId, onTilesetChange }: TilesetSelectorProps) {
  const [isCollapsed, setIsCollapsed] = useState(true)
  const tilesets = getAllTilesets()

  return (
    <div className={`tileset-selector ${isCollapsed ? 'collapsed' : ''}`}>
      {!isCollapsed ? (
        <>
          <div className="tileset-selector-label">Map Style:</div>
          <div className="tileset-buttons">
            {tilesets.map((tileset) => (
              <button
                key={tileset.id}
                className={`tileset-button ${selectedTilesetId === tileset.id ? 'active' : ''}`}
                onClick={() => onTilesetChange(tileset.id)}
                title={tileset.description}
              >
                <div
                  className="tileset-preview"
                  style={{
                    backgroundImage: `url(${getTilePreviewUrl(tileset.url)})`
                  }}
                />
                <div className="tileset-name">{tileset.name}</div>
              </button>
            ))}
          </div>
          <button
            className="tileset-collapse-button"
            onClick={() => setIsCollapsed(true)}
            title="Collapse"
          >
            v
          </button>
        </>
      ) : (
        <button
          className="tileset-expand-button"
          onClick={() => setIsCollapsed(false)}
          title="Change map style"
        >
          Map Style ^
        </button>
      )}
    </div>
  )
}
