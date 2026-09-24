import { createBrowserRouter, Navigate, useParams } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { JobLayout } from './layouts/JobLayout'
import { SettingsLayout } from './layouts/SettingsLayout'
import { RouteErrorPage } from './errors/RouteErrorPage'

import { OpportunitiesPage } from '../pages/opportunities/OpportunitiesPage'
import { DiscoverPage } from '../pages/discover/DiscoverPage'
import { NewJobPage } from '../pages/jobs/NewJobPage'
import { JobDescriptionPage } from '../pages/jobs/JobDescriptionPage'
import { JobCvPage } from '../pages/jobs/JobCvPage'
import { JobCoveragePage } from '../pages/jobs/JobCoveragePage'
import { JobApplicationPage } from '../pages/jobs/JobApplicationPage'
import { JobActivityPage } from '../pages/jobs/JobActivityPage'
import { CvLibraryPage } from '../pages/cv-library/CvLibraryPage'
import { ApplicationsPage } from '../pages/applications/ApplicationsPage'
import { ProfilePage } from '../pages/profile/ProfilePage'
import { PreferencesPage } from '../pages/preferences/PreferencesPage'
import { AiConnectionsPage } from '../pages/settings/AiConnectionsPage'
import { SearchSourcesPage } from '../pages/settings/SearchSourcesPage'
import { NotFoundPage } from '../pages/NotFoundPage'

function JobRedirect() {
  const { jobId } = useParams<{ jobId: string }>()
  return <Navigate to={`/jobs/${jobId}/description`} replace />
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        index: true,
        element: <Navigate to="/opportunities" replace />,
      },
      {
        path: 'opportunities',
        element: <OpportunitiesPage />,
      },
      {
        path: 'discover',
        element: <DiscoverPage />,
      },
      {
        path: 'jobs/new',
        element: <NewJobPage />,
      },
      {
        path: 'jobs/:jobId',
        element: <JobLayout />,
        children: [
          {
            index: true,
            element: <JobRedirect />,
          },
          {
            path: 'description',
            element: <JobDescriptionPage />,
          },
          {
            path: 'cv',
            element: <JobCvPage />,
          },
          {
            path: 'coverage',
            element: <JobCoveragePage />,
          },
          {
            path: 'application',
            element: <JobApplicationPage />,
          },
          {
            path: 'activity',
            element: <JobActivityPage />,
          },
        ],
      },
      {
        path: 'cv-library',
        element: <CvLibraryPage />,
      },
      {
        path: 'applications',
        element: <ApplicationsPage />,
      },
      {
        path: 'profile',
        element: <ProfilePage />,
      },
      {
        path: 'preferences',
        element: <PreferencesPage />,
      },
      {
        path: 'settings',
        element: <SettingsLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="/settings/ai" replace />,
          },
          {
            path: 'ai',
            element: <AiConnectionsPage />,
          },
          {
            path: 'search',
            element: <SearchSourcesPage />,
          },
        ],
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])
