import Link from "next/link";

export function SiteHeader({ showAppointment = true }: { showAppointment?: boolean }) {
  return (
    <header className="site-header">
      <div className="wrap header-row">
        <Link href="/" className="brand" aria-label="HealthCore home">
          <svg width="36" height="36" viewBox="0 0 40 40" aria-hidden="true">
            <circle cx="20" cy="20" r="20" fill="#0B5D63" />
            <path d="M20 10v20M10 20h20" stroke="white" strokeWidth="4" strokeLinecap="round" />
          </svg>
          HealthCore
        </Link>
        <nav className="nav" aria-label="Primary">
          <a href="/#home">Home</a>
          <a href="/#services">Services</a>
          <a href="/#locations">Locations</a>
          <a href="/#contact">Contact</a>
        </nav>
        {showAppointment ? (
          <div className="header-actions">
            <Link className="button" href="/appointment">
              Request an appointment
            </Link>
          </div>
        ) : null}
      </div>
    </header>
  );
}
