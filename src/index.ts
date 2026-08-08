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

console.log("--- Filtering ---");
console.log("No-show appointments:", filterAppointmentsByStatus(appointments, "no-show"));
console.log("Denied claims:", filterClaimsByStatus(claims, "denied"));

console.log("\n--- Sorting ---");
console.log("Appointments by date:", sortAppointmentsByDate(appointments, "asc").map(a => a.scheduledDate));
console.log("Claims by amount:", sortClaimsByAmount(claims, "desc").map(c => c.amount));

console.log("\n--- Search ---");
console.log("Linear search patient-2:", linearSearchPatientById(patients, "patient-2"));
console.log("Binary search patient-2:", binarySearchPatientIndexById(patients, "patient-2"));

console.log("\n--- Reports ---");
console.log("No-show rate:", calculateNoShowRate(appointments).toFixed(1) + "%");
console.log("Denial rate:", calculateDenialRate(claims).toFixed(1) + "%");
console.log("Total claim amount:", calculateTotalClaimAmount(claims));
console.log("Max claim amount:", getMaxClaimAmount(claims));
console.log("Avg CE hours:", calculateAverageCEHoursCompleted(staff));
console.log("Appointments by status:", countAppointmentsByStatus(appointments));

console.log("\n--- Validations ---");
console.log("Patient 1 valid?", isValidPatientRecord(patients[0]));
console.log("Appointment 1 valid?", isValidAppointmentRecord(appointments[0]));
console.log("Claim 2 valid?", isValidBillingClaim(claims[1]));