import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Table, TableHead, TableBody, TableRow, TableCell, TableHeader } from './Table'

describe('Table', () => {
  it('renders with children', () => {
    render(<Table><tbody><tr><td>cell</td></tr></tbody></Table>)
    expect(screen.getByText('cell')).toBeTruthy()
  })

  it('applies className', () => {
    const { container } = render(<Table className="custom" />)
    expect(container.firstChild).toHaveClass('custom')
  })
})

describe('TableHead', () => {
  it('renders and applies default styles', () => {
    const { container } = render(<TableHead><tr><th>head</th></tr></TableHead>)
    expect(container.firstChild).toHaveClass('border-b', 'border-gray-800')
  })
})

describe('TableBody', () => {
  it('renders children', () => {
    render(<TableBody><tr><td>body</td></tr></TableBody>)
    expect(screen.getByText('body')).toBeTruthy()
  })
})

describe('TableRow', () => {
  it('renders with hover styles', () => {
    const { container } = render(<TableRow><td>row</td></TableRow>)
    expect(container.firstChild).toHaveClass('hover:bg-gray-800/50')
  })
})

describe('TableCell', () => {
  it('renders with padding', () => {
    const { container } = render(<TableCell>data</TableCell>)
    expect(container.firstChild).toHaveClass('px-4', 'py-3')
  })
})

describe('TableHeader', () => {
  it('renders as th element', () => {
    const { container } = render(<TableHeader>header</TableHeader>)
    expect(container.firstChild).toHaveClass('font-medium')
  })
})
