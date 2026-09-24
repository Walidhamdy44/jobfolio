import type { Profile } from '../../../types'

export interface CVPreviewProps {
  profile: Profile
}

export function CVPreview({ profile }: CVPreviewProps) {
  return (
    <article className="cv-paper" aria-label="CV preview document">
      <h2>{profile.name}</h2>
      <p className="cv-headline">{profile.headline}</p>
      <p className="cv-contact">
        {[profile.location, profile.phone, profile.email].filter(Boolean).join(' · ')}
      </p>
      {profile.links && profile.links.length > 0 && (
        <p className="cv-contact">{profile.links.join(' · ')}</p>
      )}

      {profile.sections.map((s) => (
        <section key={s.title}>
          <h3>{s.title}</h3>
          {s.items.map((i) => (
            <p key={i.id} className={/\d{2}\/\d{4}/.test(i.text) ? 'cv-role' : ''}>
              {i.text}
            </p>
          ))}
        </section>
      ))}
    </article>
  )
}
