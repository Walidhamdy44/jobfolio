import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DynamicField } from './DynamicField'
import type { FormField } from '../../../types'

describe('DynamicField', () => {
  it('renders radio options in a fieldset with keyboard interaction', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    const field: FormField = {
      key: 'auth_work',
      label: 'Are you authorized to work in Egypt?',
      type: 'radio',
      required: true,
      options: [
        { label: 'Yes', value: 'yes' },
        { label: 'No', value: 'no' },
      ],
      value: 'yes',
    }

    render(<DynamicField field={field} value="yes" onChange={onChange} />)

    expect(screen.getByText(/Are you authorized to work in Egypt\?/)).toBeDefined()
    const yesRadio = screen.getByRole('radio', { name: 'Yes' }) as HTMLInputElement
    const noRadio = screen.getByRole('radio', { name: 'No' }) as HTMLInputElement

    expect(yesRadio.checked).toBe(true)
    expect(noRadio.checked).toBe(false)

    await user.click(noRadio)
    expect(onChange).toHaveBeenCalledWith('no')
  })

  it('renders recognized CV file upload with informative notice', () => {
    const field: FormField = {
      key: 'resume',
      label: 'Upload Resume / CV',
      type: 'file',
      required: true,
      options: [],
      value: '',
    }

    render(<DynamicField field={field} value="" onChange={() => {}} />)

    expect(screen.getByText(/Your approved PDF CV will be attached automatically/)).toBeDefined()
  })
})
