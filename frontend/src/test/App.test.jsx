import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import App from '../App'

// Mock global fetch
global.fetch = vi.fn()

describe('NovaMind Chat UI', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    localStorage.clear()
    
    // Default fetch mocks
    fetch.mockImplementation((url) => {
      if (url.endsWith('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'healthy' })
        })
      }
      if (url.endsWith('/sessions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [] })
        })
      }
      if (url.endsWith('/session/new')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ session_id: 'test-session-123' })
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      })
    })
  })

  it('renders welcome screen and description text', async () => {
    render(<App />)
    
    // Wait for health check & session creation to finish loading
    await waitFor(() => {
      expect(screen.getByText('Welcome to NovaMind')).toBeInTheDocument()
    })
    
    expect(screen.getByText(/I handle customer support with intelligent intent classification/)).toBeInTheDocument()
  })

  it('renders sidebar with New Session button', async () => {
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByText(/New Session/i)).toBeInTheDocument()
    })
  })

  it('toggles dark/light theme', async () => {
    render(<App />)
    
    await waitFor(() => {
      const themeBtn = screen.getByTitle(/Switch to/i)
      expect(themeBtn).toBeInTheDocument()
      
      // Default theme is dark
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      
      // Toggle theme
      fireEvent.click(themeBtn)
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
      expect(localStorage.getItem('novamind_theme')).toBe('light')
    })
  })

  it('mode selector switches between Support and NovaMind AI', async () => {
    render(<App />)
    
    await waitFor(() => {
      const supportBtn = screen.getByText(/🤖 Support/i)
      const aiBtn = screen.getByText(/⚡ NovaMind AI/i)
      
      expect(supportBtn).toBeInTheDocument()
      expect(aiBtn).toBeInTheDocument()
      
      // Click AI Mode
      fireEvent.click(aiBtn)
      expect(screen.getByText('NovaMind Conversational Core Active', { exact: false })).toBeInTheDocument()
    })
  })
})
