// Meshtastic role enum mapping
// Based on Meshtastic protobufs: https://github.com/meshtastic/protobufs/blob/master/meshtastic/config.proto
export const MESHTASTIC_ROLES: Record<string, string> = {
  '0': 'Client',
  '1': 'Client Mute',
  '2': 'Router',
  '3': 'Router Client',
  '4': 'Repeater',
  '5': 'Tracker',
  '6': 'Sensor',
  '7': 'TAK',
  '8': 'Client Hidden',
  '9': 'Lost and Found',
  '10': 'TAK Tracker',
  '11': 'Router Late',
  '12': 'Client Base',
}

export function getRoleName(roleCode: string): string {
  return MESHTASTIC_ROLES[roleCode] || `Role ${roleCode}`
}

// Meshtastic hardware model enum mapping
// Based on Meshtastic protobufs: https://github.com/meshtastic/protobufs/blob/master/meshtastic/mesh.proto
// Hardware images from: https://github.com/meshtastic/web-flasher/tree/main/public/images
export interface HardwareInfo {
  name: string
  displayName: string
  imageUrl?: string
}

/**
 * Official Meshtastic hardware display names mapping
 * Based on Meshtastic documentation: https://meshtastic.org/docs/hardware/devices/
 */
const OFFICIAL_HARDWARE_NAMES: Record<string, string> = {
  'RAK4631': 'RAK4631',
  'T_ECHO': 'T-Echo',
  'TBEAM': 'T-Beam',
  'HELTEC_V2_0': 'Heltec V2.0',
  'HELTEC_V2_1': 'Heltec V2.1',
  'HELTEC_V1': 'Heltec V1',
  'HELTEC_V3': 'Heltec V3', // Official name from Meshtastic web flasher
  'HELTEC_V4': 'Heltec V4', // Official name from Meshtastic web flasher
  'NANO_G1': 'Nano G1',
  'NANO_G1_EXPLORER': 'Nano G1 Explorer',
  'NANO_G2_ULTRA': 'Nano G2 Ultra',
  'STATION_G1': 'Station G1',
  'STATION_G2': 'Station G2',
  'LILYGO_TBEAM_S3_CORE': 'Lilygo T-Beam S3 Core', // Match MeshMonitor pattern
  'T_DECK': 'T-Deck',
  'T_DECK_PRO': 'T-Deck Pro',
  'T_WATCH_S3': 'T-Watch S3',
  'T_WATCH_ULTRA': 'T-Watch Ultra',
  'T_ECHO_LITE': 'T-Echo Lite',
  'T_LORA_PAGER': 'T-LoRa Pager',
  'HELTEC_WIRELESS_TRACKER': 'Heltec Wireless Tracker',
  'HELTEC_WIRELESS_TRACKER_V1_0': 'Heltec Wireless Tracker v1.0', // Fixed: MeshMonitor has "V1 0"
  'HELTEC_WIRELESS_TRACKER_V2': 'Heltec Wireless Tracker V2',
  'HELTEC_WIRELESS_PAPER': 'Heltec Wireless Paper',
  'HELTEC_WIRELESS_PAPER_V1_0': 'Heltec Wireless Paper v1.0', // Fixed: MeshMonitor has "V1 0"
  'HELTEC_WIRELESS_BRIDGE': 'Heltec Wireless Bridge', // Not in MeshMonitor - verified against web flasher
  'HELTEC_WSL_V3': 'Heltec WSL V3',
  'HELTEC_WSL_V3_PLUS': 'Heltec WSL V3 Plus', // Not in MeshMonitor - verified against web flasher
  'HELTEC_HRU_3601': 'Heltec HRU 3601', // Match MeshMonitor pattern
  'HELTEC_VISION_MASTER_T190': 'Heltec Vision Master T190',
  'HELTEC_VISION_MASTER_E213': 'Heltec Vision Master E213',
  'HELTEC_VISION_MASTER_E290': 'Heltec Vision Master E290',
  'HELTEC_MESH_NODE_T114': 'Heltec Mesh Node T114',
  'HELTEC_MESH_POCKET': 'Heltec Mesh Pocket',
  'HELTEC_MESH_SOLAR': 'Heltec Mesh Solar',
  'HELTEC_SENSOR_HUB': 'Heltec Sensor Hub',
  'HELTEC_HT62': 'Heltec HT62',
  'HELTEC_V3_PLUS': 'Heltec V3 Plus', // Not in MeshMonitor - verified against web flasher
  'HELTEC_CAPSULE_SENSOR_V3': 'Heltec Capsule Sensor V3', // Added from MeshMonitor
  'RAK11200': 'RAK11200',
  'RAK11310': 'RAK11310', // RAK should be fully capitalized
  'RAK2560': 'RAK2560',
  'RAK3172': 'RAK3172',
  'RAK3312': 'RAK3312', // RAK should be fully capitalized
  'RAK3401': 'RAK3401',
  'RAK6421': 'RAK6421',
  'TLORA_V1': 'T-LoRa V1',
  'TLORA_V2': 'T-LoRa V2',
  'TLORA_V1_1P3': 'T-LoRa V1.1.3', // Match MeshMonitor pattern (fixed formatting)
  'TLORA_V2_1_1P6': 'T-LoRa V2.1.1.6', // Match MeshMonitor pattern (fixed formatting)
  'TLORA_V2_1_1P8': 'T-LoRa V2.1.1.8', // Match MeshMonitor pattern (fixed formatting)
  'TLORA_T3_S3': 'T-LoRa T3 S3', // Match MeshMonitor pattern
  'TLORA_C6': 'T-LoRa C6',
  'TBEAM_V0P7': 'T-Beam V0.7', // Match MeshMonitor pattern (capital V)
  'SEEED_WIO_TRACKER_L1': 'Seeed Wio Tracker L1', // Match MeshMonitor pattern
  'SEEED_WIO_TRACKER_L1_EINK': 'Seeed Wio Tracker L1 Eink', // Match MeshMonitor pattern
  'SEEED_SOLAR_NODE': 'Seeed Solar Node', // Match MeshMonitor pattern
  'SENSECAP_INDICATOR': 'SenseCap Indicator', // Match MeshMonitor pattern
  'TRACKER_T1000_E': 'Tracker T1000 E', // Match MeshMonitor pattern
  'WIO_WM1110': 'Wio WM1110',
  'WIO_E5': 'Wio E5',
  'XIAO_NRF52_KIT': 'Xiao nRF52 Kit', // Match MeshMonitor pattern
  'RPI_PICO': 'RPI Pico', // Match MeshMonitor pattern
  'RPI_PICO2': 'RPI Pico2', // Match MeshMonitor pattern
  'RP2040_LORA': 'RP2040 LoRa',
  'RP2040_FEATHER_RFM95': 'RP2040 Feather RFM95',
  'PICOMPUTER_S3': 'PiComputer S3', // Match MeshMonitor pattern
  'M5STACK': 'M5Stack',
  'M5STACK_COREBASIC': 'M5Stack CoreBasic', // Match MeshMonitor pattern
  'M5STACK_CORE2': 'M5Stack Core2',
  'M5STACK_C6L': 'M5Stack C6L',
  'M5STACK_CARDPUTER_ADV': 'M5Stack Cardputer Advanced',
  'M5STACK_RESERVED': 'M5Stack Reserved',
  'BETAFPV_2400_TX': 'BetaFPV 2400 TX',
  'BETAFPV_900_NANO_TX': 'BetaFPV 900 Nano TX',
  'SENSELORA_RP2040': 'SenseLoRA RP2040',
  'SENSELORA_S3': 'SenseLoRA S3',
  'CANARYONE': 'CanaryOne',
  'LORA_TYPE': 'LoRa Type', // Match MeshMonitor pattern
  'LORA_RELAY_V1': 'LoRa Relay V1',
  'WIPHONE': 'WiPhone',
  'WISMESH_TAP': 'WisMesh Tap', // Match MeshMonitor pattern
  'WISMESH_TAP_V2': 'WisMesh TAP V2',
  'WISMESH_TAG': 'WisMesh Tag',
  'ROUTASTIC': 'Routastic',
  'MESH_TAB': 'Mesh Tab',
  'MESHLINK': 'MeshLink',
  'THINKNODE_M1': 'ThinkNode M1',
  'THINKNODE_M2': 'ThinkNode M2',
  'THINKNODE_M3': 'ThinkNode M3',
  'THINKNODE_M4': 'ThinkNode M4',
  'THINKNODE_M5': 'ThinkNode M5',
  'THINKNODE_M6': 'ThinkNode M6',
  'T_ETH_ELITE': 'T Eth Elite', // Match MeshMonitor pattern
  'MUZI_BASE': 'Muzi Base',
  'MUZI_R1_NEO': 'Muzi R1 Neo',
  'NOMADSTAR_METEOR_PRO': 'NomadStar Meteor Pro',
  'CROWPANEL': 'CrowPanel',
  'LINK_32': 'Link 32',
  'MS24SF1': 'MS24SF1',
  'NRF52840DK': 'Nrf52840dk', // Match MeshMonitor pattern
  'NRF52840_PCA10059': 'nRF52840 Pca10059', // Match MeshMonitor pattern
  'NRF52_UNKNOWN': 'nRF52 Unknown',
  'NRF52_PROMICRO_DIY': 'nRF52 ProMicro DIY',
  'PORTDUINO': 'Portduino',
  'ANDROID_SIM': 'Android Sim',
  'DIY_V1': 'DIY V1',
  'DR_DEV': 'DR Dev',
  'EBYTE_ESP32_S3': 'EByte ESP32 S3', // Match MeshMonitor pattern
  'ESP32_S3_PICO': 'ESP32 S3 Pico', // Match MeshMonitor pattern
  'CHATTER_2': 'Chatter 2',
  'UNPHONE': 'Unphone',
  'TD_LORAC': 'TD LoRaC',
  'CDEBYTE_EORA_S3': 'CDebyte Eora S3', // Match MeshMonitor pattern
  'TWC_MESH_V4': 'TWC Mesh V4',
  'RADIOMASTER_900_BANDIT': 'RadioMaster 900 Bandit', // Match MeshMonitor pattern
  'RADIOMASTER_900_BANDIT_NANO': 'RadioMaster 900 Bandit Nano', // Match MeshMonitor pattern
  'ME25LS01_4Y10TD': 'ME25LS01 4Y10TD',
  'UNSET': 'Unset',
  'PRIVATE_HW': 'Private HW', // Match MeshMonitor pattern
}

/**
 * Prettifies a hardware model name for display using official Meshtastic names
 * Falls back to a formatted version if no official name is found
 */
function prettifyHardwareName(name: string): string {
  // Check if we have an official name
  if (OFFICIAL_HARDWARE_NAMES[name]) {
    return OFFICIAL_HARDWARE_NAMES[name]
  }

  // Handle special cases
  if (name === 'UNSET' || name === 'PRIVATE_HW') {
    return name
  }

  // Fallback: format the name intelligently
  let prettified = name
    // Handle version numbers first: "V2_0" -> "V2.0", "V0P7" -> "V0.7"
    .replace(/V(\d+)_(\d+)/g, 'V$1.$2')
    .replace(/V(\d+)P(\d+)/g, 'V$1.$2')
    // Handle "P" versions: "1P6" -> "1.6", "1P3" -> "1.3"
    .replace(/(\d+)P(\d+)/g, '$1.$2')
    // Replace underscores with spaces
    .replace(/_/g, ' ')
    // Add space before numbers after letters (e.g., "RAK4631" -> "RAK 4631")
    .replace(/([A-Z])(\d)/g, '$1 $2')
    // Add space after numbers before letters
    .replace(/(\d)([A-Z])/g, '$1 $2')
    // Capitalize first letter of each word, but keep acronyms (all caps, 2+ chars) intact
    .split(' ')
    .map((word) => {
      // Keep acronyms (all caps, 2+ chars) as-is
      if (word.length >= 2 && word === word.toUpperCase() && /^[A-Z]+$/.test(word)) {
        return word
      }
      // Capitalize first letter, lowercase the rest
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    })
    .join(' ')

  return prettified
}

// Helper to generate image URL from hardware name
// Images are from: https://github.com/meshtastic/web-flasher/tree/main/public/img/devices
// Note: Not all hardware models have images available
function getImageUrl(name: string): string | undefined {
  // Convert enum name to lowercase with hyphens (as used in web-flasher)
  // Examples: RAK4631 -> rak4631, T_ECHO -> t-echo, HELTEC_V2_0 -> heltec-v2-0
  const imageName = name.toLowerCase().replace(/_/g, '-')
  return `https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/${imageName}.svg`
}

export const MESHTASTIC_HARDWARE: Record<string, Omit<HardwareInfo, 'displayName'>> = {
  '0': { name: 'UNSET', imageUrl: undefined },
  '1': { name: 'TLORA_V2', imageUrl: undefined }, // No image available
  '2': { name: 'TLORA_V1', imageUrl: undefined }, // No image available
  '3': { name: 'TLORA_V2_1_1P6', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/tlora-v2-1-1_6.svg' }, // Uses underscore in version
  '4': { name: 'TBEAM', imageUrl: getImageUrl('tbeam') },
  '5': { name: 'HELTEC_V2_0', imageUrl: undefined }, // No image available
  '6': { name: 'TBEAM_V0P7', imageUrl: undefined }, // No image available
  '7': { name: 'T_ECHO', imageUrl: getImageUrl('t-echo') },
  '8': { name: 'TLORA_V1_1P3', imageUrl: undefined },
  '9': { name: 'RAK4631', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/rak4631_case.svg' }, // Using case variant
  '10': { name: 'HELTEC_V2_1', imageUrl: undefined }, // No image available
  '11': { name: 'HELTEC_V1', imageUrl: undefined }, // No image available
  '12': { name: 'LILYGO_TBEAM_S3_CORE', imageUrl: getImageUrl('tbeam-s3-core') },
  '13': { name: 'RAK11200', imageUrl: getImageUrl('rak11200') },
  '14': { name: 'NANO_G1', imageUrl: undefined }, // No image available
  '15': { name: 'TLORA_V2_1_1P8', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/tlora-v2-1-1_8.svg' }, // Uses underscore in version
  '16': { name: 'TLORA_T3_S3', imageUrl: getImageUrl('tlora-t3s3-v1') },
  '17': { name: 'NANO_G1_EXPLORER', imageUrl: undefined }, // No image available
  '18': { name: 'NANO_G2_ULTRA', imageUrl: getImageUrl('nano-g2-ultra') },
  '19': { name: 'LORA_TYPE', imageUrl: undefined },
  '20': { name: 'WIPHONE', imageUrl: undefined },
  '21': { name: 'WIO_WM1110', imageUrl: getImageUrl('wio-tracker-wm1110') },
  '22': { name: 'RAK2560', imageUrl: getImageUrl('rak2560') },
  '23': { name: 'HELTEC_HRU_3601', imageUrl: undefined },
  '24': { name: 'HELTEC_WIRELESS_BRIDGE', imageUrl: undefined },
  '25': { name: 'STATION_G1', imageUrl: undefined }, // No image available
  '26': { name: 'RAK11310', imageUrl: getImageUrl('rak11310') },
  '27': { name: 'SENSELORA_RP2040', imageUrl: undefined },
  '28': { name: 'SENSELORA_S3', imageUrl: undefined },
  '29': { name: 'CANARYONE', imageUrl: undefined },
  '30': { name: 'RP2040_LORA', imageUrl: undefined }, // No image available
  '31': { name: 'STATION_G2', imageUrl: getImageUrl('station-g2') },
  '32': { name: 'LORA_RELAY_V1', imageUrl: undefined },
  '33': { name: 'NRF52840DK', imageUrl: undefined },
  '34': { name: 'PPR', imageUrl: undefined },
  '35': { name: 'GENIEBLOCKS', imageUrl: undefined },
  '36': { name: 'NRF52_UNKNOWN', imageUrl: undefined },
  '37': { name: 'PORTDUINO', imageUrl: undefined },
  '38': { name: 'ANDROID_SIM', imageUrl: undefined },
  '39': { name: 'DIY_V1', imageUrl: getImageUrl('diy') },
  '40': { name: 'NRF52840_PCA10059', imageUrl: undefined },
  '41': { name: 'DR_DEV', imageUrl: undefined },
  '42': { name: 'M5STACK', imageUrl: undefined },
  '43': { name: 'HELTEC_V3', imageUrl: getImageUrl('heltec-v3') },
  '44': { name: 'HELTEC_WSL_V3', imageUrl: getImageUrl('heltec-wsl-v3') },
  '45': { name: 'BETAFPV_2400_TX', imageUrl: undefined }, // No image available
  '46': { name: 'BETAFPV_900_NANO_TX', imageUrl: undefined }, // No image available
  '47': { name: 'RPI_PICO', imageUrl: getImageUrl('pico') }, // Uses 'pico' not 'rpi-pico'
  '48': { name: 'HELTEC_WIRELESS_TRACKER', imageUrl: getImageUrl('heltec-wireless-tracker') },
  '49': { name: 'HELTEC_WIRELESS_PAPER', imageUrl: getImageUrl('heltec-wireless-paper') },
  '50': { name: 'T_DECK', imageUrl: getImageUrl('t-deck') },
  '51': { name: 'T_WATCH_S3', imageUrl: getImageUrl('t-watch-s3') },
  '52': { name: 'PICOMPUTER_S3', imageUrl: undefined }, // No image available
  '53': { name: 'HELTEC_HT62', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/heltec-ht62-esp32c3-sx1262.svg' }, // Full filename
  '54': { name: 'EBYTE_ESP32_S3', imageUrl: getImageUrl('seeed-xiao-s3') },
  '55': { name: 'ESP32_S3_PICO', imageUrl: undefined },
  '56': { name: 'CHATTER_2', imageUrl: undefined },
  '57': { name: 'HELTEC_WIRELESS_PAPER_V1_0', imageUrl: undefined },
  '58': { name: 'HELTEC_WIRELESS_TRACKER_V1_0', imageUrl: undefined },
  '59': { name: 'UNPHONE', imageUrl: undefined },
  '60': { name: 'TD_LORAC', imageUrl: undefined },
  '61': { name: 'CDEBYTE_EORA_S3', imageUrl: undefined },
  '62': { name: 'TWC_MESH_V4', imageUrl: undefined },
  '63': { name: 'NRF52_PROMICRO_DIY', imageUrl: getImageUrl('promicro') },
  '64': { name: 'RADIOMASTER_900_BANDIT_NANO', imageUrl: undefined },
  '65': { name: 'HELTEC_CAPSULE_SENSOR_V3', imageUrl: undefined },
  '66': { name: 'HELTEC_VISION_MASTER_T190', imageUrl: getImageUrl('heltec-vision-master-t190') },
  '67': { name: 'HELTEC_VISION_MASTER_E213', imageUrl: getImageUrl('heltec-vision-master-e213') },
  '68': { name: 'HELTEC_VISION_MASTER_E290', imageUrl: getImageUrl('heltec-vision-master-e290') },
  '69': { name: 'HELTEC_MESH_NODE_T114', imageUrl: getImageUrl('heltec-mesh-node-t114-case') },
  '70': { name: 'SENSECAP_INDICATOR', imageUrl: getImageUrl('seeed-sensecap-indicator') },
  '71': { name: 'TRACKER_T1000_E', imageUrl: getImageUrl('tracker-t1000-e') },
  '72': { name: 'RAK3172', imageUrl: undefined },
  '73': { name: 'WIO_E5', imageUrl: undefined },
  '74': { name: 'RADIOMASTER_900_BANDIT', imageUrl: undefined },
  '75': { name: 'ME25LS01_4Y10TD', imageUrl: undefined },
  '76': { name: 'RP2040_FEATHER_RFM95', imageUrl: undefined },
  '77': { name: 'M5STACK_COREBASIC', imageUrl: undefined },
  '78': { name: 'M5STACK_CORE2', imageUrl: undefined },
  '79': { name: 'RPI_PICO2', imageUrl: getImageUrl('rpipicow') },
  '80': { name: 'HELTEC_V3_PLUS', imageUrl: undefined }, // No image available
  '81': { name: 'HELTEC_WSL_V3_PLUS', imageUrl: undefined }, // No image available
  '82': { name: 'MS24SF1', imageUrl: undefined },
  '83': { name: 'TLORA_C6', imageUrl: undefined },
  '84': { name: 'WISMESH_TAP', imageUrl: getImageUrl('rak-wismeshtap') },
  '85': { name: 'ROUTASTIC', imageUrl: undefined },
  '86': { name: 'MESH_TAB', imageUrl: undefined },
  '87': { name: 'MESHLINK', imageUrl: undefined },
  '88': { name: 'XIAO_NRF52_KIT', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/seeed_xiao_nrf52_kit.svg' }, // Uses underscore
  '89': { name: 'THINKNODE_M1', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/thinknode_m1.svg' }, // Uses underscore, same image as M5
  '90': { name: 'THINKNODE_M2', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/thinknode_m2.svg' }, // Uses underscore
  '91': { name: 'T_ETH_ELITE', imageUrl: undefined },
  '92': { name: 'HELTEC_SENSOR_HUB', imageUrl: undefined },
  '93': { name: 'MUZI_BASE', imageUrl: undefined },
  '94': { name: 'HELTEC_MESH_POCKET', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/heltec_mesh_pocket.svg' }, // Uses underscore
  '95': { name: 'SEEED_SOLAR_NODE', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/seeed_solar.svg' }, // Uses underscore
  '96': { name: 'NOMADSTAR_METEOR_PRO', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/meteor_pro.svg' }, // Uses underscore
  '97': { name: 'CROWPANEL', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/crowpanel_3_5.svg' }, // Uses underscore, multiple sizes available
  '98': { name: 'LINK_32', imageUrl: undefined },
  '99': { name: 'SEEED_WIO_TRACKER_L1', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/wio_tracker_l1_case.svg' }, // Uses underscore
  '100': { name: 'SEEED_WIO_TRACKER_L1_EINK', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/wio_tracker_l1_eink.svg' }, // Uses underscore
  '101': { name: 'MUZI_R1_NEO', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/muzi_r1_neo.svg' }, // Uses underscore
  '102': { name: 'T_DECK_PRO', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/tdeck_pro.svg' }, // Uses underscore
  '103': { name: 'T_LORA_PAGER', imageUrl: getImageUrl('lilygo-tlora-pager') },
  '104': { name: 'M5STACK_RESERVED', imageUrl: undefined },
  '105': { name: 'WISMESH_TAG', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/rak_wismesh_tag.svg' }, // Uses underscore
  '106': { name: 'RAK3312', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/rak_3312.svg' }, // Uses underscore
  '107': { name: 'THINKNODE_M5', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/thinknode_m1.svg' }, // Image filename is thinknode_m1.svg but it's for M5
  '108': { name: 'HELTEC_MESH_SOLAR', imageUrl: undefined },
  '109': { name: 'T_ECHO_LITE', imageUrl: undefined },
  '110': { name: 'HELTEC_V4', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/heltec_v4.svg' }, // Uses underscore, not hyphen
  '111': { name: 'M5STACK_C6L', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/m5_c6l.svg' }, // Uses underscore
  '112': { name: 'M5STACK_CARDPUTER_ADV', imageUrl: undefined },
  '113': { name: 'HELTEC_WIRELESS_TRACKER_V2', imageUrl: undefined },
  '114': { name: 'T_WATCH_ULTRA', imageUrl: undefined },
  '115': { name: 'THINKNODE_M3', imageUrl: 'https://raw.githubusercontent.com/meshtastic/web-flasher/main/public/img/devices/thinknode_m3.svg' }, // Uses underscore
  '116': { name: 'WISMESH_TAP_V2', imageUrl: undefined },
  '117': { name: 'RAK3401', imageUrl: undefined },
  '118': { name: 'RAK6421', imageUrl: undefined },
  '119': { name: 'THINKNODE_M4', imageUrl: undefined },
  '120': { name: 'THINKNODE_M6', imageUrl: undefined },
  '255': { name: 'PRIVATE_HW', imageUrl: undefined },
}

export function getHardwareInfo(hwModel: string | number | null | undefined): HardwareInfo {
  if (hwModel === null || hwModel === undefined) {
    return { name: 'Unknown', displayName: 'Unknown', imageUrl: undefined }
  }
  
  const key = String(hwModel)
  
  // First try direct lookup by numeric key
  if (MESHTASTIC_HARDWARE[key]) {
    const info = MESHTASTIC_HARDWARE[key]
    return {
      ...info,
      displayName: prettifyHardwareName(info.name)
    }
  }
  
  // If not found, try to find by name (case-insensitive)
  const hwModelUpper = key.toUpperCase()
  for (const info of Object.values(MESHTASTIC_HARDWARE)) {
    if (info.name.toUpperCase() === hwModelUpper) {
      return {
        ...info,
        displayName: prettifyHardwareName(info.name)
      }
    }
  }
  
  // If still not found, return the original value as name
  return { name: key, displayName: prettifyHardwareName(key), imageUrl: undefined }
}

export function getHardwareName(hwModel: string | number | null | undefined): string {
  const info = getHardwareInfo(hwModel)
  return prettifyHardwareName(info.name)
}
