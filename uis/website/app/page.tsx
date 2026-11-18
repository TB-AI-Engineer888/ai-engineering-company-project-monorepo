import Link from "next/link";
import { SiteHeader } from "./site-header";

const services = [
  {
    title: "Primary Care & Chronic Disease",
    points: [
      "Same-day appointments with primary care physicians",
      "Ongoing management of diabetes, hypertension, and asthma",
    ],
  },
  {
    title: "Specialist Consultations",
    points: [
      "Cardiology, endocrinology, pulmonology, and women's health",
      "Referrals coordinated within the HealthCore network",
    ],
  },
  {
    title: "Preventive Health & Wellbeing",
    points: [
      "Screenings, vaccinations, and annual check-ups",
      "Mental health counselling and psychiatry referrals",
    ],
  },
];

const reasons = [
  "Same-day appointments at most locations",
  "Extended hours — weekdays until 7pm or 8pm, Saturdays available",
  "Bilingual staff in English and Spanish at US locations",
  "12 clinics across Texas, Florida, Georgia, and the United Kingdom",
];

const locations = [
  ["HealthCore Austin Central", "Austin, TX", "(512) 340-8800", "Mon–Fri 7am–8pm · Sat 9am–3pm"],
  ["HealthCore Austin North", "Austin, TX", "(512) 340-8810", "Mon–Fri 8am–7pm"],
  ["HealthCore San Antonio", "San Antonio, TX", "(210) 720-4400", "Mon–Fri 8am–6pm · Sat 9am–1pm"],
  ["HealthCore Miami", "Miami, FL", "(305) 510-7700", "Mon–Fri 7am–8pm · Sat 9am–4pm"],
  ["HealthCore Orlando", "Orlando, FL", "(407) 892-6600", "Mon–Fri 8am–6pm"],
  ["HealthCore Atlanta", "Atlanta, GA", "(404) 330-9900", "Mon–Fri 8am–7pm"],
];

export default function HomePage() {
  return (
    <>
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <SiteHeader />
      <main id="main">
        <section className="hero" id="home" aria-labelledby="hero-heading">
          <div className="wrap hero-inner">
            <h1 id="hero-heading">Healthcare that fits your life</h1>
            <p className="lede">
              12 outpatient clinics across the US and UK offering same-day appointments, extended hours, and
              bilingual care — so you can get the attention you need, when you need it.
            </p>
            <p>
              <Link className="button" href="/appointment">
                Request an appointment
              </Link>
            </p>
            <p className="fine">
              Founded in 2011 · Trusted outpatient care across Texas, Florida, Georgia, and the UK
            </p>
          </div>
        </section>

        <section className="section" id="services" aria-labelledby="services-heading">
          <div className="wrap">
            <div className="center">
              <h2 id="services-heading">Services</h2>
            </div>
            <div className="cards">
              {services.map((service) => (
                <article className="card" key={service.title}>
                  <h3>{service.title}</h3>
                  <ul>
                    {service.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section why-band" aria-labelledby="why-heading">
          <div className="wrap">
            <h2 className="center" id="why-heading">
              Why HealthCore
            </h2>
            <div className="why">
              {reasons.map((reason) => (
                <p key={reason}>{reason}</p>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="locations" aria-labelledby="locations-heading">
          <div className="wrap">
            <div className="center">
              <h2 id="locations-heading">Our US Locations</h2>
              <p className="muted">Six clinics across Texas, Florida, and Georgia.</p>
            </div>
            <div className="locations">
              {locations.map(([name, city, phone, hours]) => (
                <article className="location" key={name}>
                  <h3>{name}</h3>
                  <p className="muted">{city}</p>
                  <p>{phone}</p>
                  <p className="muted">{hours}</p>
                </article>
              ))}
            </div>
            <p className="center muted">
              UK clinics serve a separate market and are not included in this public-facing website.
            </p>
          </div>
        </section>

        <section className="section contact" id="contact" aria-labelledby="contact-heading">
          <div className="wrap center">
            <h2 id="contact-heading">Contact</h2>
            <div className="contact-grid">
              <p>
                <strong>General enquiries</strong>
                info@healthcore.com
              </p>
              <p>
                <strong>Austin HQ</strong>
                (512) 340-8800
              </p>
              <p>
                <strong>Miami</strong>
                (305) 510-7700
              </p>
            </div>
            <p>UK (London): +44 20 7946 0100</p>
            <p>
              <Link className="button" href="/appointment">
                Request an appointment
              </Link>
            </p>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <div className="wrap footer-row">
          <p>© 2025 HealthCore. All rights reserved.</p>
          <nav aria-label="Social media">
            <a href="https://linkedin.com/company/healthcore">LinkedIn</a>
            <a href="https://facebook.com/healthcore">Facebook</a>
            <a href="https://instagram.com/healthcore">Instagram</a>
          </nav>
        </div>
      </footer>
    </>
  );
}
