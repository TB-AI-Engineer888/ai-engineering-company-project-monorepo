import type { Metadata } from "next";
import { EnquiryForm } from "../enquiry-form";
import { SiteHeader } from "../site-header";

export const metadata: Metadata = {
  title: "HealthCore — Patient Enquiry Form",
  description:
    "Submit a patient enquiry to HealthCore. The front desk confirms the appointment. This is not live booking.",
};

export default function AppointmentPage() {
  return (
    <>
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <SiteHeader showAppointment={false} />
      <main id="main" className="wrap">
        <div className="page-intro center">
          <h1>Patient Enquiry Form</h1>
          <p className="muted">
            Tell us a little about yourself and what you need. Our front desk will call you back to confirm your
            appointment — this is not a live booking.
          </p>
        </div>
        <p className="notice">
          Are you a healthcare provider or organisation looking to partner with HealthCore? Contact our operations
          team at <a href="mailto:partnerships@healthcore.com">partnerships@healthcore.com</a>.
        </p>
        <EnquiryForm />
      </main>
    </>
  );
}
