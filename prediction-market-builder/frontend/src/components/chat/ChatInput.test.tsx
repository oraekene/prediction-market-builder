import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInput from './ChatInput'

vi.mock('@/lib/websocket', () => ({
  chatWs: { send: vi.fn() },
}))

describe('ChatInput', () => {
  it('renders input field and send button', () => {
    render(<ChatInput />)
    expect(screen.getByPlaceholderText(/ask me anything/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /send/i })).toBeTruthy()
  })

  it('calls onSend callback on submit', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    const input = screen.getByPlaceholderText(/ask me anything/i)
    await userEvent.type(input, 'test message')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(onSend).toHaveBeenCalledWith('test message')
  })

  it('clears input after submit', async () => {
    render(<ChatInput />)
    const input = screen.getByPlaceholderText(/ask me anything/i) as HTMLInputElement
    await userEvent.type(input, 'hello')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(input.value).toBe('')
  })

  it('does not call onSend for empty input', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    await userEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(onSend).not.toHaveBeenCalled()
  })
})
