import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { AddJobForm } from '../../features/jobs/components/AddJobForm'
import { useAddJobMutation, useImportJobMutation } from '../../features/jobs/queries'

export function NewJobPage() {
  const navigate = useNavigate()
  const addJobMutation = useAddJobMutation()
  const importJobMutation = useImportJobMutation()

  const handleSave = async (jobData: {
    url: string
    title: string
    company: string
    location: string
    description: string
  }) => {
    const res = await addJobMutation.mutateAsync(jobData)
    if (res.job?.id) {
      navigate(`/jobs/${res.job.id}/description`)
    } else {
      navigate('/opportunities')
    }
  }

  const handleImport = async (url: string) => {
    const res = await importJobMutation.mutateAsync({ url })
    if (res.job?.id) {
      navigate(`/jobs/${res.job.id}/description`)
    } else {
      navigate('/opportunities')
    }
  }

  return (
    <div>
      <Link to="/opportunities" className="text-button back-button">
        <ArrowLeft size={16} />
        Back to opportunities
      </Link>
      <AddJobForm
        busy={addJobMutation.isPending || importJobMutation.isPending}
        onSave={handleSave}
        onImport={handleImport}
      />
    </div>
  )
}
