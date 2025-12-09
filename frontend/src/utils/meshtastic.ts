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
