import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatMessage from './ChatMessage'

describe('ChatMessage', () => {
  it('renders user message right-aligned', () => {
    render(<ChatMessage role="user" content="Hello" />)
    const wrapper = screen.getByText('Hello').closest('.mb-3')
    expect(wrapper?.className).toContain('justify-end')
  })

  it('renders assistant message left-aligned', () => {
    render(<ChatMessage role="assistant" content="Hi there" />)
    const wrapper = screen.getByText('Hi there').closest('.mb-3')
    expect(wrapper?.className).toContain('justify-start')
  })

  it('renders system message with system styling', () => {
    render(<ChatMessage role="system" content="System note" />)
    const bubble = screen.getByText('System note').parentElement
    expect(bubble?.className).toContain('italic')
    expect(bubble?.className).toContain('text-gray-400')
  })

  it('displays content text', () => {
    render(<ChatMessage role="user" content="Message content" />)
    expect(screen.getByText('Message content')).toBeTruthy()
  })

  it('shows timestamp when provided', () => {
    render(<ChatMessage role="user" content="hi" timestamp="10:30 AM" />)
    expect(screen.getByText('10:30 AM')).toBeTruthy()
  })

  it('hides timestamp when not provided', () => {
    render(<ChatMessage role="user" content="hi" />)
    expect(screen.queryByText(/AM|PM/)).toBeNull()
  })
})
