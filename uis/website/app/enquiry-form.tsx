"use client";

import { FormEvent, useState } from "react";

const clinics = [
  "HealthCore Austin Central",
  "HealthCore Austin North",
  "HealthCore San Antonio",
  "HealthCore Miami",
  "HealthCore Orlando",
  "HealthCore Atlanta",
];

export function EnquiryForm() {
  const [submitted, setSubmitted] = useState(false);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="success" role="alert">
        <h2>Thank you for reaching out to HealthCore.</h2>
        <p>
          We have received your enquiry. A member of our front desk team will contact you within 1 business day
          to confirm your appointment details and answer any questions.
        </p>
        <p>This is not a live booking. If you need urgent assistance, call your preferred clinic directly.</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate={false}>
      <fieldset>
        <legend>Your details</legend>
        <div className="form-grid">
          <label>
            First name
            <input name="first_name" required minLength={2} maxLength={50} autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input name="last_name" required minLength={2} maxLength={50} autoComplete="family-name" />
          </label>
          <label>
            Date of birth
            <input name="date_of_birth" type="date" required />
          </label>
          <label>
            Email address
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <label className="span-2">
            Phone number
            <input name="phone" type="tel" required placeholder="+1 305 555 0191" autoComplete="tel" />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Appointment preferences</legend>
        <div className="form-grid">
          <label>
            Preferred language
            <select name="preferred_language" required defaultValue="">
              <option value="" disabled>
                Select an option
              </option>
              <option value="english">English</option>
              <option value="spanish">Spanish</option>
            </select>
          </label>
          <label>
            Preferred clinic
            <select name="preferred_clinic" required defaultValue="">
              <option value="" disabled>
                Select an option
              </option>
              {clinics.map((clinic) => (
                <option key={clinic} value={clinic}>
                  {clinic}
                </option>
              ))}
            </select>
          </label>
          <label>
            Preferred date
            <input name="preferred_date" type="date" required />
          </label>
          <label>
            Preferred time of day
            <select name="preferred_time" required defaultValue="">
              <option value="" disabled>
                Select an option
              </option>
              <option value="morning">Morning (7am–12pm)</option>
              <option value="afternoon">Afternoon (12pm–5pm)</option>
              <option value="evening">Evening (5pm–8pm)</option>
            </select>
          </label>
          <label className="span-2">
            Service needed
            <select name="service_type" required defaultValue="">
              <option value="" disabled>
                Select an option
              </option>
              <option value="primary_care">Primary Care</option>
              <option value="chronic_disease">Chronic Disease Management</option>
              <option value="specialist">Specialist Consultation</option>
              <option value="preventive">Preventive Health</option>
              <option value="womens_health">Women&apos;s Health</option>
              <option value="paediatric">Paediatric Care</option>
              <option value="mental_health">Mental Health</option>
            </select>
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Your health concern</legend>
        <label>
          Brief description of your health concern
          <textarea name="health_concern" required minLength={20} maxLength={500} rows={4} />
        </label>
      </fieldset>

      <fieldset>
        <label className="choices">
          <input name="contact_consent" type="checkbox" required />
          <span>I consent to HealthCore contacting me about this enquiry.</span>
        </label>
      </fieldset>

      <div className="actions">
        <button className="button" type="submit">
          Submit enquiry
        </button>
        <button className="button secondary" type="reset">
          Clear form
        </button>
      </div>
    </form>
  );
}
