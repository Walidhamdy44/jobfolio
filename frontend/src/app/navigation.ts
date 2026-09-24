import {
  BriefcaseBusiness,
  FileText,
  ListChecks,
  UserRound,
  SlidersHorizontal,
  PlugZap,
  Search,
} from 'lucide-react'

export interface NavItem {
  id: string
  name: string
  path: string
  icon: typeof BriefcaseBusiness
  dividerBefore?: boolean
}

export const MAIN_NAV: NavItem[] = [
  { id: 'opportunities', name: 'Opportunities', path: '/opportunities', icon: BriefcaseBusiness },
  { id: 'discover', name: 'Discover', path: '/discover', icon: Search },
  { id: 'library', name: 'CV library', path: '/cv-library', icon: FileText },
  { id: 'tracker', name: 'Applications', path: '/applications', icon: ListChecks },
  { id: 'profile', name: 'My profile', path: '/profile', icon: UserRound, dividerBefore: true },
  { id: 'preferences', name: 'Search preferences', path: '/preferences', icon: SlidersHorizontal },
  { id: 'settings', name: 'Connections', path: '/settings/ai', icon: PlugZap },
]
