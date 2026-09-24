import { Link, useOutletContext } from 'react-router-dom'
import { FileText, Download, ArrowRight } from 'lucide-react'
import { Empty } from '../../shared/ui/Empty'
import type { Bootstrap } from '../../types'

export function CvLibraryPage() {
  const { data } = useOutletContext<{ data?: Bootstrap }>()

  const jobsWithCv = data?.jobs?.filter((j) => j.score !== undefined) || []

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Your CV library</h1>
          <p>One source of truth. A considered version for every role.</p>
        </div>
        <a className="button" href="/api/master-cv" target="_blank" rel="noreferrer">
          <Download size={16} />
          Master CV (PDF)
        </a>
      </div>

      {jobsWithCv.length > 0 ? (
        <div className="library-list" role="list">
          {jobsWithCv.map((j) => (
            <div className="library-row" key={j.id} role="listitem">
              <FileText size={27} aria-hidden="true" />
              <div>
                <h2>{j.title}</h2>
                <p>
                  {j.company} · {j.score}% coverage
                </p>
              </div>
              <div className="button-group">
                <a
                  className="button"
                  href={`/api/jobs/${j.id}/documents/pdf`}
                  download
                >
                  <Download size={15} />
                  PDF
                </a>
                <a
                  className="button"
                  href={`/api/jobs/${j.id}/documents/docx`}
                  download
                >
                  Word
                </a>
                <Link to={`/jobs/${j.id}/cv`} className="button">
                  Review
                  <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          icon="cv"
          title="Every role deserves its own CV"
          action={
            <Link to="/opportunities" className="button primary">
              Explore opportunities
              <ArrowRight size={16} />
            </Link>
          }
        >
          Prepare a CV from a saved job to start your library. Your original CV stays unchanged.
        </Empty>
      )}
    </>
  )
}
