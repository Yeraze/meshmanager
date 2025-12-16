import { describe, it, expect } from 'vitest'
import { HARDWARE_MODELS, getHardwareModelName, formatHardwareModelName } from './hardware'

describe('hardware utilities', () => {
  describe('HARDWARE_MODELS', () => {
    it('should have hardware model mappings', () => {
      // Should have a reasonable number of mappings (116 as of current protobufs)
      expect(Object.keys(HARDWARE_MODELS).length).toBeGreaterThan(100)
    })

    it('should have correct model names for common hardware', () => {
      expect(HARDWARE_MODELS[0]).toBe('UNSET')
      expect(HARDWARE_MODELS[9]).toBe('RAK4631')
      expect(HARDWARE_MODELS[43]).toBe('HELTEC_V3')
      expect(HARDWARE_MODELS[50]).toBe('T_DECK')
      expect(HARDWARE_MODELS[110]).toBe('HELTEC_V4')
      expect(HARDWARE_MODELS[255]).toBe('PRIVATE_HW')
    })
  })

  describe('getHardwareModelName', () => {
    it('should return correct name for known hardware models (number input)', () => {
      expect(getHardwareModelName(43)).toBe('HELTEC_V3')
      expect(getHardwareModelName(9)).toBe('RAK4631')
      expect(getHardwareModelName(0)).toBe('UNSET')
      expect(getHardwareModelName(50)).toBe('T_DECK')
    })

    it('should handle string input (as returned by API)', () => {
      expect(getHardwareModelName('43')).toBe('HELTEC_V3')
      expect(getHardwareModelName('9')).toBe('RAK4631')
      expect(getHardwareModelName('0')).toBe('UNSET')
    })

    it('should return Unknown for invalid model numbers', () => {
      expect(getHardwareModelName(999)).toBe('Unknown (999)')
      expect(getHardwareModelName(256)).toBe('Unknown (256)')
      expect(getHardwareModelName(-1)).toBe('Unknown (-1)')
    })

    it('should handle null and undefined', () => {
      expect(getHardwareModelName(null)).toBe('N/A')
      expect(getHardwareModelName(undefined)).toBe('N/A')
    })

    it('should return non-numeric strings as-is', () => {
      expect(getHardwareModelName('CUSTOM_HARDWARE')).toBe('CUSTOM_HARDWARE')
      expect(getHardwareModelName('invalid')).toBe('invalid')
    })
  })

  describe('formatHardwareModelName', () => {
    it('should format names to readable text', () => {
      expect(formatHardwareModelName(43)).toBe('Heltec v3')
      expect(formatHardwareModelName(48)).toBe('Heltec Wireless Tracker')
      expect(formatHardwareModelName(50)).toBe('T Deck')
      expect(formatHardwareModelName(31)).toBe('Station G2')
    })

    it('should preserve uppercase abbreviations', () => {
      expect(formatHardwareModelName(9)).toBe('RAK4631')
      expect(formatHardwareModelName(47)).toBe('RPI Pico')
      expect(formatHardwareModelName(38)).toBe('Android Sim')
    })

    it('should preserve N/A and Unknown values', () => {
      expect(formatHardwareModelName(null)).toBe('N/A')
      expect(formatHardwareModelName(undefined)).toBe('N/A')
      expect(formatHardwareModelName(999)).toBe('Unknown (999)')
    })

    it('should handle string input from API', () => {
      expect(formatHardwareModelName('43')).toBe('Heltec v3')
      expect(formatHardwareModelName('9')).toBe('RAK4631')
    })
  })
})
