import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { Package } from '../../types'
import { useReviewJobMutation } from '../jobs/queries'

export interface ReviewDraftContextValue {
  cvChecked: boolean
  setCVChecked: (checked: boolean) => void
  coverageChecked: boolean
  setCoverageChecked: (checked: boolean) => void
  answers: Record<string, string>
  setAnswers: (answers: Record<string, string>) => void
  setAnswer: (key: string, val: string) => void
  supports: ('full' | 'partial' | 'missing')[]
  setSupports: React.Dispatch<React.SetStateAction<('full' | 'partial' | 'missing')[]>>
  setSupportIndex: (index: number, val: 'full' | 'partial' | 'missing') => void
  isDirty: boolean
  isConflicted: boolean
  baseHash: string
  saveReview: () => Promise<void>
  resetToPackage: () => void
  isSaving: boolean
  saveError: string
}

const ReviewDraftContext = createContext<ReviewDraftContextValue | null>(null)

export function useReviewDraft() {
  const ctx = useContext(ReviewDraftContext)
  if (!ctx) throw new Error('useReviewDraft must be used within ReviewDraftProvider')
  return ctx
}

export interface ReviewDraftProviderProps {
  jobId: string
  pkg: Package | null
  children: ReactNode
}

export function ReviewDraftProvider({ jobId, pkg, children }: ReviewDraftProviderProps) {
  const [baseHash, setBaseHash] = useState(pkg?.hash || '')
  const [cvChecked, setCVCheckedState] = useState(pkg?.cv_reviewed || false)
  const [coverageChecked, setCoverageCheckedState] = useState(pkg?.coverage_reviewed || false)
  const [answers, setAnswersState] = useState<Record<string, string>>(pkg?.answers || {})
  const [supports, setSupportsState] = useState<('full' | 'partial' | 'missing')[]>(
    pkg?.requirements.map((r) => r.support) || []
  )
  const [hasUserEdits, setHasUserEdits] = useState(false)
  const [isConflicted, setIsConflicted] = useState(false)
  const [saveError, setSaveError] = useState('')

  const reviewMutation = useReviewJobMutation(jobId)

  // Sync baseline whenever pkg arrives or updates
  useEffect(() => {
    if (!pkg) return

    // If initial load or unedited package update
    if (!baseHash || (!hasUserEdits && pkg.hash !== baseHash)) {
      setBaseHash(pkg.hash)
      setCVCheckedState(pkg.cv_reviewed || false)
      setCoverageCheckedState(pkg.coverage_reviewed || false)
      setAnswersState(pkg.answers || {})
      setSupportsState(pkg.requirements.map((r) => r.support) || [])
      setIsConflicted(false)
    } else if (hasUserEdits && pkg.hash !== baseHash) {
      // User has edits and server generated a new package version
      setIsConflicted(true)
    }
  }, [pkg?.hash, baseHash, hasUserEdits])

  const setCVChecked = (checked: boolean) => {
    setCVCheckedState(checked)
    setHasUserEdits(true)
  }

  const setCoverageChecked = (checked: boolean) => {
    setCoverageCheckedState(checked)
    setHasUserEdits(true)
  }

  const setAnswers = (newAnswers: Record<string, string>) => {
    setAnswersState(newAnswers)
    setHasUserEdits(true)
  }

  const setAnswer = (key: string, val: string) => {
    setAnswersState((prev) => ({ ...prev, [key]: val }))
    setHasUserEdits(true)
  }

  const setSupports = (
    action: React.SetStateAction<('full' | 'partial' | 'missing')[]>
  ) => {
    setSupportsState(action)
    setHasUserEdits(true)
  }

  const setSupportIndex = (index: number, val: 'full' | 'partial' | 'missing') => {
    setSupportsState((prev) => prev.map((item, i) => (i === index ? val : item)))
    setHasUserEdits(true)
  }

  const isDirty = Boolean(
    pkg &&
      (cvChecked !== (pkg.cv_reviewed || false) ||
        coverageChecked !== (pkg.coverage_reviewed || false) ||
        JSON.stringify(answers) !== JSON.stringify(pkg.answers || {}) ||
        JSON.stringify(supports) !== JSON.stringify(pkg.requirements.map((r) => r.support) || []))
  )

  const resetToPackage = () => {
    if (!pkg) return
    setBaseHash(pkg.hash)
    setCVCheckedState(pkg.cv_reviewed || false)
    setCoverageCheckedState(pkg.coverage_reviewed || false)
    setAnswersState(pkg.answers || {})
    setSupportsState(pkg.requirements.map((r) => r.support) || [])
    setIsConflicted(false)
    setHasUserEdits(false)
    setSaveError('')
  }

  const saveReview = async () => {
    if (!pkg) return
    setSaveError('')
    const targetHash = baseHash || pkg.hash
    const resolvedSupports =
      supports.length === pkg.requirements.length
        ? supports
        : pkg.requirements.map((r) => r.support)

    try {
      await reviewMutation.mutateAsync({
        package_hash: targetHash,
        cv_reviewed: cvChecked,
        coverage_reviewed: coverageChecked,
        answers,
        supports: resolvedSupports,
      })
      setBaseHash(pkg.hash)
      setHasUserEdits(false)
      setIsConflicted(false)
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Failed to save review.'
      setSaveError(msg)
      throw err
    }
  }

  return (
    <ReviewDraftContext.Provider
      value={{
        cvChecked,
        setCVChecked,
        coverageChecked,
        setCoverageChecked,
        answers,
        setAnswers,
        setAnswer,
        supports,
        setSupports,
        setSupportIndex,
        isDirty,
        isConflicted,
        baseHash,
        saveReview,
        resetToPackage,
        isSaving: reviewMutation.isPending,
        saveError,
      }}
    >
      {children}
    </ReviewDraftContext.Provider>
  )
}
