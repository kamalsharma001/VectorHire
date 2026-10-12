/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        ocean: {
          DEFAULT: '#075985',       // Deep Ocean Blue
          dark: '#0C4A6E',          // Midnight Ocean Dark
          rich: '#0369A1',          // Rich Oceanic Blue
          hover: '#0284C7',         // Ocean Hover
          light: '#F0F9FF',         // Pale blue surface tint
          border: '#BAE6FD',        // Luminous sky border
        },
        cyan: {
          DEFAULT: '#06B6D4',       // Electric Cyan
          hover: '#0891B2',
          dark: '#0E7490',
          light: '#ECFEFF',         // Cyan surface tint
          border: '#A5F3FC',        // Cyan border
          glow: 'rgba(6, 182, 212, 0.25)',
        },
        mint: {
          DEFAULT: '#00D294',       // Luminous Mint
          hover: '#00B882',
          dark: '#0B5B44',          // High-contrast accessible text
          light: '#E8FBF5',         // Mint surface tint
          border: '#A3F3DC',        // Mint border tint
          glow: 'rgba(0, 210, 148, 0.25)',
        },
        violet: {
          DEFAULT: '#8B5CF6',       // Selective Violet AI accent
          hover: '#7C3AED',
          dark: '#5B21B6',
          light: '#F5F3FF',         // Violet surface tint
          border: '#DDD6FE',        // Violet border tint
          glow: 'rgba(139, 92, 246, 0.25)',
        },
        slate: {
          blue: '#075985',          // Compatibility
          blueHover: '#0369A1',
          blueDark: '#0C4A6E',
          blueLight: '#F0F9FF',
          blueBorder: '#BAE6FD',
        },
        ink: {
          DEFAULT: '#0F172A',       // Slate 900 Primary text
          secondary: '#475569',     // Slate 600 Secondary text
          muted: '#64748B',         // Slate 500 Muted text
          faint: '#94A3B8',         // Slate 400
        },
        surface: {
          DEFAULT: '#FFFFFF',       // Crisp White
          secondary: '#F8FAFC',     // Light Canvas Slate 50
          subtle: '#F1F5F9',        // Slate 100
          border: '#E2E8F0',        // Clean subtle border
          borderStrong: '#CBD5E1',  // Stronger border
          blue: '#F0F9FF',          // Oceanic surface
          cyan: '#ECFEFF',          // Cyan surface
          mint: '#E8FBF5',          // Mint surface
          violet: '#F5F3FF',        // Violet surface
        },
        brand: {
          primary: '#075985',       // Deep Ocean Blue
          rich: '#0369A1',          // Rich Blue
          cyan: '#06B6D4',          // Electric Cyan
          mint: '#00D294',          // Luminous Mint
          secondary: '#00D294',     // Luminous Mint
          accent: '#06B6D4',        // Electric Cyan
          violet: '#8B5CF6',        // Selective Violet
          dark: '#0F172A',          // Ink
          light: '#FFFFFF',
          soft: '#F8FAFC',
        },
        semantic: {
          success: '#0B5B44',       // High-contrast mint text
          successBg: '#E8FBF5',
          successBorder: '#A3F3DC',
          warning: '#92400E',       // Amber warning text
          warningBg: '#FFFBEB',
          warningBorder: '#FDE68A',
          error: '#9F1239',         // Rose / Crimson error text
          errorBg: '#FFF1F2',
          errorBorder: '#FECDD3',
          missing: '#475569',       // Muted missing text
          missingBg: '#F1F5F9',
          missingBorder: '#E2E8F0',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.04)',
        'elevated': '0 10px 25px -4px rgba(15, 23, 42, 0.08), 0 4px 10px -2px rgba(15, 23, 42, 0.04)',
        'card-hover': '0 14px 28px -4px rgba(7, 89, 133, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.06)',
        'glow-blue': '0 0 20px -3px rgba(3, 105, 161, 0.35), 0 4px 10px rgba(7, 89, 133, 0.15)',
        'glow-cyan': '0 0 20px -3px rgba(6, 182, 212, 0.35), 0 4px 10px rgba(6, 182, 212, 0.15)',
        'glow-mint': '0 0 20px -3px rgba(0, 210, 148, 0.35), 0 4px 10px rgba(0, 210, 148, 0.15)',
        'glow-violet': '0 0 20px -3px rgba(139, 92, 246, 0.35), 0 4px 10px rgba(139, 92, 246, 0.15)',
        'drawer': '-10px 0 35px -5px rgba(15, 23, 42, 0.2)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-up': 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
