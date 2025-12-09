/**
 * Available map tilesets configuration
 */

export type TilesetId = 'cartoDark' | 'cartoLight' | 'osm' | 'osmHot' | 'openTopo' | 'esriSatellite'

export interface TilesetConfig {
  readonly id: TilesetId
  readonly name: string
  readonly url: string
  readonly attribution: string
  readonly maxZoom: number
  readonly description: string
}

export const TILESETS: Record<TilesetId, TilesetConfig> = {
  cartoDark: {
    id: 'cartoDark',
    name: 'Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 19,
    description: 'Dark theme map'
  },
  cartoLight: {
    id: 'cartoLight',
    name: 'Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 19,
    description: 'Light theme map'
  },
  osm: {
    id: 'osm',
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
    description: 'Standard OpenStreetMap tiles'
  },
  osmHot: {
    id: 'osmHot',
    name: 'Humanitarian',
    url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, Tiles by <a href="https://www.hotosm.org/">HOT</a>',
    maxZoom: 19,
    description: 'Humanitarian OpenStreetMap Team style'
  },
  openTopo: {
    id: 'openTopo',
    name: 'Topographic',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="https://opentopomap.org">OpenTopoMap</a>',
    maxZoom: 17,
    description: 'Topographic map with elevation contours'
  },
  esriSatellite: {
    id: 'esriSatellite',
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
    maxZoom: 18,
    description: 'Satellite imagery'
  }
}

export const DEFAULT_TILESET_ID: TilesetId = 'cartoDark'

export function getTilesetById(id: string): TilesetConfig {
  if (id in TILESETS) {
    return TILESETS[id as TilesetId]
  }
  return TILESETS[DEFAULT_TILESET_ID]
}

export function getAllTilesets(): TilesetConfig[] {
  return Object.values(TILESETS)
}

// Generate a preview tile URL for a specific location
function getTilePreviewUrl(templateUrl: string): string {
  return templateUrl
    .replace('{z}', '4')
    .replace('{x}', '3')
    .replace('{y}', '6')
    .replace('{s}', 'a')
    .replace('{r}', '')
}

export { getTilePreviewUrl }
