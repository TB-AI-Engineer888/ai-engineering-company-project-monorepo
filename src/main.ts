import { appointments, claims, patients, staff } from "./data/sampleData";
import {
  filterAppointmentsByStatus,
  filterClaimsByStatus,
  sortAppointmentsByDate,
  sortClaimsByAmount,
} from "./utils/collections";
import {
  linearSearchPatientById,
  binarySearchPatientIndexById,
} from "./utils/search";
import {
  calculateNoShowRate,
  calculateDenialRate,
  calculateTotalClaimAmount,
  getMaxClaimAmount,
  calculateAverageCEHoursCompleted,
  countAppointmentsByStatus,
} from "./utils/transformations";
import {
  isValidPatientRecord,
  isValidAppointmentRecord,
  isValidBillingClaim,
} from "./utils/validations";

const app = document.getElementById("app")!;

app.innerHTML = `
  <div style="font-family: sans-serif; max-width: 900px; margin: 2rem auto; color: #e2e8f0;">
    <h1 style="font-size: 1.5rem; font-weight: bold;">HealthCore Utils Test Page</h1>
    <p style="color: #94a3b8; margin-bottom: 1.5rem;">Filter, search, sort, and generate reports using the real HealthCore functions.</p>

    <section style="margin-bottom: 1.5rem;">
      <h2 style="font-weight: 600;">Filter</h2>
      <button id="filterNoShow">No-show appointments</button>
      <button id="filterDenied">Denied claims</button>
      <pre id="filterOutput" style="background:#1e293b; padding:1rem; overflow:auto;"></pre>
    </section>

    <section style="margin-bottom: 1.5rem;">
      <h2 style="font-weight: 600;">Sort</h2>
      <button id="sortDate">Appointments by date</button>
      <button id="sortAmount">Claims by amount (desc)</button>
      <pre id="sortOutput" style="background:#1e293b; padding:1rem; overflow:auto;"></pre>
    </section>

    <section style="margin-bottom: 1.5rem;">
      <h2 style="font-weight: 600;">Search</h2>
      <input id="searchId" placeholder="e.g. patient-2" />
      <button id="searchBtn">Search patient</button>
      <pre id="searchOutput" style="background:#1e293b; padding:1rem; overflow:auto;"></pre>
    </section>

    <section style="margin-bottom: 1.5rem;">
      <h2 style="font-weight: 600;">Generate Reports</h2>
      <button id="reportBtn">Run all reports</button>
      <pre id="reportOutput" style="background:#1e293b; padding:1rem; overflow:auto;"></pre>
    </section>

    <section>
      <h2 style="font-weight: 600;">Validate</h2>
      <button id="validatePatient">Check patient-1</button>
      <button id="validateAppt">Check appt-1</button>
      <button id="validateClaim">Check claim-2 (denied)</button>
      <pre id="validateOutput" style="background:#1e293b; padding:1rem; overflow:auto;"></pre>
    </section>
  </div>
`;

// Filter
document.getElementById("filterNoShow")!.addEventListener("click", () => {
  const result = filterAppointmentsByStatus(appointments, "no-show");
  document.getElementById("filterOutput")!.textContent = JSON.stringify(result, null, 2);
});
document.getElementById("filterDenied")!.addEventListener("click", () => {
  const result = filterClaimsByStatus(claims, "denied");
  document.getElementById("filterOutput")!.textContent = JSON.stringify(result, null, 2);
});

// Sort
document.getElementById("sortDate")!.addEventListener("click", () => {
  const result = sortAppointmentsByDate(appointments, "asc");
  document.getElementById("sortOutput")!.textContent = JSON.stringify(result.map(a => a.scheduledDate), null, 2);
});
document.getElementById("sortAmount")!.addEventListener("click", () => {
  const result = sortClaimsByAmount(claims, "desc");
  document.getElementById("sortOutput")!.textContent = JSON.stringify(result.map(c => c.amount), null, 2);
});

// Search
document.getElementById("searchBtn")!.addEventListener("click", () => {
  const id = (document.getElementById("searchId") as HTMLInputElement).value.trim();
  const linear = linearSearchPatientById(patients, id);
  const binaryIndex = binarySearchPatientIndexById(patients, id);
  document.getElementById("searchOutput")!.textContent =
    `Linear search: ${linear ? JSON.stringify(linear) : "not found"}\nBinary search index: ${binaryIndex}`;
});

// Reports
document.getElementById("reportBtn")!.addEventListener("click", () => {
  const output = {
    noShowRate: calculateNoShowRate(appointments).toFixed(1) + "%",
    denialRate: calculateDenialRate(claims).toFixed(1) + "%",
    totalClaimAmount: calculateTotalClaimAmount(claims),
    maxClaimAmount: getMaxClaimAmount(claims),
    avgCEHours: calculateAverageCEHoursCompleted(staff),
    appointmentsByStatus: countAppointmentsByStatus(appointments),
  };
  document.getElementById("reportOutput")!.textContent = JSON.stringify(output, null, 2);
});

// Validate
document.getElementById("validatePatient")!.addEventListener("click", () => {
  document.getElementById("validateOutput")!.textContent =
    `Patient 1 valid? ${isValidPatientRecord(patients[0])}`;
});
document.getElementById("validateAppt")!.addEventListener("click", () => {
  document.getElementById("validateOutput")!.textContent =
    `Appointment 1 valid? ${isValidAppointmentRecord(appointments[0])}`;
});
document.getElementById("validateClaim")!.addEventListener("click", () => {
  document.getElementById("validateOutput")!.textContent =
    `Claim 2 valid? ${isValidBillingClaim(claims[1])}`;
});