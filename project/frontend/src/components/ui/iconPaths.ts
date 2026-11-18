/**
 * Inline SVG path registry.
 *
 * The prototype shipped every icon as an inline path with no icon dependency;
 * this keeps that behaviour and adds type safety over the icon names.
 */
export const ICON_PATHS = {
  home: 'M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z',
  plan: 'M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM14 3v5h5M9 13h6M9 17h4',
  progress: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  mic: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3',
  micOff:
    'M9 9v3a3 3 0 0 0 5.1 2.1M15 9.3V6a3 3 0 0 0-5.7-1.3M5 11a7 7 0 0 0 11.3 5.5M19 11a7 7 0 0 1-.7 3M12 18v3M3 3l18 18',
  bell: 'M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0',
  chevronRight: 'M9 6l6 6-6 6',
  chevronLeft: 'M15 6l-6 6 6 6',
  chevronDown: 'M6 9l6 6 6-6',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  close: 'M6 6l12 12M18 6 6 18',
  play: 'M8 5.5v13l11-6.5z',
  pause: 'M8 5h3v14H8zM13 5h3v14h-3z',
  replay: 'M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4',
  skip: 'M6 5.5v13l9-6.5zM18 5v14',
  cc: 'M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM10 10.5a2 2 0 1 0 0 3M17 10.5a2 2 0 1 0 0 3',
  sparkle:
    'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6',
  calendar:
    'M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM4 10h16M8 3v4M16 3v4',
  flag: 'M5 21V4M5 4h11l-2 4 2 4H5',
  lock: 'M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5z',
  share: 'M12 3v12M7 8l5-5 5 5M5 14v6h14v-6',
  info: 'M12 8h.01M11 12h1v5h1M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  phoneEnd: 'M3 14.5c5-4.5 13-4.5 18 0l-2 2.5-3.5-1.5V13c-2.3-.7-4.7-.7-7 0v2.5L5 17z',
  wifiOff:
    'M2 8.5a15 15 0 0 1 5-2.8M10.5 5.1A15 15 0 0 1 22 8.5M5 12a10 10 0 0 1 4.5-2.3M14.5 9.7A10 10 0 0 1 19 12M8.5 15.5a5 5 0 0 1 7 0M12 19h.01M3 3l18 18',
  users:
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21v-1a6 6 0 0 1 12 0v1M16 3.5a4 4 0 1 1 0 7M22 21v-1a6 6 0 0 0-4-5.6',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  chart: 'M4 20V4M4 20h16M8 16l4-5 3 3 5-6',
  arrowRight: 'M5 12h14M13 6l6 6-6 6',
  message: 'M5 4h14a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H9l-5 4V5a1 1 0 0 1 1-1z',
  edit: 'M4 20h4L19 9l-4-4L4 16zM14 6l4 4',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
} as const

export type IconName = keyof typeof ICON_PATHS
