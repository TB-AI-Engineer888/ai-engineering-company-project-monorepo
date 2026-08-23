/* ============================================================
   HealthCore — validation.js
   Two responsibilities in this one file (per the required
   project file structure):
   1. Language toggle shared by index.html and application.html
   2. Patient enquiry form validation (application.html only)
   ============================================================ */

/* ---------- 1. Translations for dynamically-generated text ---------- */
const T = {
  en: {
    errors: {
      first_name: "First name must contain only letters and be at least 2 characters",
      last_name: "Last name must contain only letters and be at least 2 characters",
      date_of_birth: "Enter a valid date of birth. Patient must be between 0 and 120 years old",
      email: "Enter a valid email address (example: name@provider.com)",
      phone: "Phone must include a country code (example: +1 305 555 0191)",
      preferred_language: "Select your preferred language",
      preferred_clinic: "Select the clinic you would like to visit",
      preferred_date: "Select a date at least 1 business day from today and no more than 60 days ahead",
      preferred_time: "Select your preferred time of day",
      service_type: "Select the type of care you are looking for",
      service_type_paediatric: "Paediatric Care is available for patients under 18. Please check the date of birth or select a different service.",
      new_patient: "Please indicate whether this is your first visit to HealthCore",
      has_insurance: "Please indicate whether you have health insurance",
      insurance_provider: "Please enter your insurance provider name",
      insurance_member_id: "Member ID must be between 6 and 20 alphanumeric characters",
      contact_consent: "You must consent to being contacted before submitting this form",
      patient_id: "Patient ID must be in the format HC- followed by 6 alphanumeric characters"
    },
    healthConcernError: (remaining) => `Please describe your health concern in at least 20 characters (${remaining} characters remaining)`,
    counter: (len) => `${len} / 500 characters`,
    options: {
      opt_select: "Select an option",
      opt_lang_en: "English",
      opt_lang_es: "Spanish",
      opt_time_morning: "Morning (7am–12pm)",
      opt_time_afternoon: "Afternoon (12pm–5pm)",
      opt_time_evening: "Evening (5pm–8pm)",
      opt_svc_primary: "Primary Care",
      opt_svc_chronic: "Chronic Disease Management",
      opt_svc_specialist: "Specialist Consultation",
      opt_svc_preventive: "Preventive Health",
      opt_svc_womens: "Women's Health",
      opt_svc_paediatric: "Paediatric Care",
      opt_svc_mental: "Mental Health"
    }
  },
  es: {
    errors: {
      first_name: "El nombre debe contener solo letras y tener al menos 2 caracteres",
      last_name: "El apellido debe contener solo letras y tener al menos 2 caracteres",
      date_of_birth: "Ingresa una fecha de nacimiento válida. El paciente debe tener entre 0 y 120 años",
      email: "Ingresa un correo electrónico válido (ejemplo: nombre@proveedor.com)",
      phone: "El teléfono debe incluir un código de país (ejemplo: +1 305 555 0191)",
      preferred_language: "Selecciona tu idioma preferido",
      preferred_clinic: "Selecciona la clínica que deseas visitar",
      preferred_date: "Selecciona una fecha con al menos 1 día hábil de anticipación y no más de 60 días",
      preferred_time: "Selecciona tu horario preferido",
      service_type: "Selecciona el tipo de atención que buscas",
      service_type_paediatric: "La Atención Pediátrica está disponible para pacientes menores de 18 años. Verifica la fecha de nacimiento o selecciona otro servicio.",
      new_patient: "Indica si esta es tu primera visita a HealthCore",
      has_insurance: "Indica si tienes seguro médico",
      insurance_provider: "Ingresa el nombre de tu compañía de seguros",
      insurance_member_id: "El número de afiliado debe tener entre 6 y 20 caracteres alfanuméricos",
      contact_consent: "Debes dar tu consentimiento para ser contactado antes de enviar este formulario",
      patient_id: "El ID de paciente debe tener el formato HC- seguido de 6 caracteres alfanuméricos"
    },
    healthConcernError: (remaining) => `Describe tu motivo de consulta en al menos 20 caracteres (${remaining} caracteres restantes)`,
    counter: (len) => `${len} / 500 caracteres`,
    options: {
      opt_select: "Selecciona una opción",
      opt_lang_en: "Inglés",
      opt_lang_es: "Español",
      opt_time_morning: "Mañana (7am–12pm)",
      opt_time_afternoon: "Tarde (12pm–5pm)",
      opt_time_evening: "Noche (5pm–8pm)",
      opt_svc_primary: "Atención Primaria",
      opt_svc_chronic: "Manejo de Enfermedades Crónicas",
      opt_svc_specialist: "Consulta con Especialista",
      opt_svc_preventive: "Salud Preventiva",
      opt_svc_womens: "Salud de la Mujer",
      opt_svc_paediatric: "Atención Pediátrica",
      opt_svc_mental: "Salud Mental"
    }
  }
};

/* ---------- 2. Language toggle (shared by both pages) ---------- */
function getCurrentLang() {
  return document.documentElement.getAttribute('data-lang') || 'en';
}

function setLanguage(lang) {
  document.documentElement.setAttribute('data-lang', lang);
  document.documentElement.lang = lang;

  // Swap every element tagged with data-lang, scoped to <body> so the
  // <html data-lang="..."> state attribute itself is never matched/hidden.
  document.querySelectorAll('body [data-lang]').forEach((el) => {
    el.hidden = el.getAttribute('data-lang') !== lang;
  });

  // Swap dynamic pieces (select option labels) that can't hold nested spans.
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (T[lang].options[key]) el.textContent = T[lang].options[key];
  });

  const enBtn = document.getElementById('lang-en-btn');
  const esBtn = document.getElementById('lang-es-btn');
  if (enBtn && esBtn) {
    enBtn.setAttribute('aria-pressed', String(lang === 'en'));
    esBtn.setAttribute('aria-pressed', String(lang === 'es'));
    [enBtn, esBtn].forEach((btn) => btn.classList.remove('bg-brand-600', 'text-white'));
    (lang === 'en' ? enBtn : esBtn).classList.add('bg-brand-600', 'text-white');
  }

  localStorage.setItem('hc-lang', lang);

  // Re-render language-dependent dynamic text that's already on screen
  // (a live error message or the character counter shouldn't go stale
  // mid-conversation when the visitor switches language).
  if (typeof refreshDynamicText === 'function') refreshDynamicText();
}

function initLanguageToggle() {
  const enBtn = document.getElementById('lang-en-btn');
  const esBtn = document.getElementById('lang-es-btn');
  if (!enBtn || !esBtn) return;

  const stored = localStorage.getItem('hc-lang');
  setLanguage(stored === 'es' ? 'es' : 'en');

  enBtn.addEventListener('click', () => setLanguage('en'));
  esBtn.addEventListener('click', () => setLanguage('es'));
}

document.addEventListener('DOMContentLoaded', initLanguageToggle);

/* ============================================================
   3. Patient enquiry form validation (application.html only)
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('enquiry-form');
  if (!form) return; // index.html has no form — nothing below applies

  const fields = {
    first_name: document.getElementById('first_name'),
    last_name: document.getElementById('last_name'),
    date_of_birth: document.getElementById('date_of_birth'),
    email: document.getElementById('email'),
    phone: document.getElementById('phone'),
    preferred_language: document.getElementById('preferred_language'),
    preferred_clinic: document.getElementById('preferred_clinic'),
    preferred_date: document.getElementById('preferred_date'),
    preferred_time: document.getElementById('preferred_time'),
    service_type: document.getElementById('service_type'),
    insurance_provider: document.getElementById('insurance_provider'),
    insurance_member_id: document.getElementById('insurance_member_id'),
    patient_id: document.getElementById('patient_id'),
    health_concern: document.getElementById('health_concern'),
    contact_consent: document.getElementById('contact_consent')
  };

  const patientIdWrapper = document.getElementById('patient-id-wrapper');
  const insuranceWrapper = document.getElementById('insurance-wrapper');
  const eveningWarning = document.getElementById('evening-warning');
  const healthConcernCounter = document.getElementById('health_concern-counter');
  const successMessage = document.getElementById('success-message');

  /* ---------- Generic show/clear error pair (§1.18 textbook pattern) ---------- */
  function showError(input, message) {
    const errorEl = document.getElementById(input.id + '-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.remove('hidden');
    }
    input.setAttribute('aria-invalid', 'true');
    input.classList.add('border-red-500');
  }

  function clearError(input) {
    const errorEl = document.getElementById(input.id + '-error');
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
    input.setAttribute('aria-invalid', 'false');
    input.classList.remove('border-red-500');
  }

  /* Radio groups don't map to a single input id, so they get their own pair. */
  function showGroupError(errorId, message) {
    const el = document.getElementById(errorId);
    if (el) {
      el.textContent = message;
      el.classList.remove('hidden');
    }
  }
  function clearGroupError(errorId) {
    const el = document.getElementById(errorId);
    if (el) {
      el.textContent = '';
      el.classList.add('hidden');
    }
  }

  function getRadioValue(name) {
    const checked = form.querySelector(`input[name="${name}"]:checked`);
    return checked ? checked.value : '';
  }

  /* ---------- Date helpers ---------- */
  function calculateAge(dob, ref) {
    let age = ref.getFullYear() - dob.getFullYear();
    const m = ref.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && ref.getDate() < dob.getDate())) age--;
    return age;
  }

  function addBusinessDays(date, days) {
    const result = new Date(date);
    let added = 0;
    while (added < days) {
      result.setDate(result.getDate() + 1);
      const day = result.getDay();
      if (day !== 0 && day !== 6) added++;
    }
    return result;
  }

  const CLINIC_EVENING_CLOSE = {
    'HealthCore Austin Central': 20,
    'HealthCore Austin North': 19,
    'HealthCore San Antonio': 18,
    'HealthCore Miami': 20,
    'HealthCore Orlando': 18,
    'HealthCore Atlanta': 19
  };

  /* ---------- Field validators — each returns true/false and manages its own error UI ---------- */
  function validateFirstName() {
    const input = fields.first_name;
    const lang = getCurrentLang();
    const value = input.value.trim();
    const ok = /^[A-Za-zÀ-ÖØ-öø-ÿñÑ\s'-]{2,50}$/.test(value);
    ok ? clearError(input) : showError(input, T[lang].errors.first_name);
    return ok;
  }

  function validateLastName() {
    const input = fields.last_name;
    const lang = getCurrentLang();
    const value = input.value.trim();
    const ok = /^[A-Za-zÀ-ÖØ-öø-ÿñÑ\s'-]{2,50}$/.test(value);
    ok ? clearError(input) : showError(input, T[lang].errors.last_name);
    return ok;
  }

  function validateDateOfBirth() {
    const input = fields.date_of_birth;
    const lang = getCurrentLang();
    let ok = false;
    if (input.value) {
      const dob = new Date(input.value + 'T00:00:00');
      const now = new Date();
      if (dob <= now) {
        const age = calculateAge(dob, now);
        ok = age >= 0 && age <= 120;
      }
    }
    ok ? clearError(input) : showError(input, T[lang].errors.date_of_birth);
    validatePaediatricCrossCheck();
    return ok;
  }

  function validateEmail() {
    const input = fields.email;
    const lang = getCurrentLang();
    const ok = input.value.trim() !== '' && input.validity.valid;
    ok ? clearError(input) : showError(input, T[lang].errors.email);
    return ok;
  }

  function validatePhone() {
    const input = fields.phone;
    const lang = getCurrentLang();
    const ok = /^\+[0-9]{1,3}[0-9\s]{6,14}$/.test(input.value.trim());
    ok ? clearError(input) : showError(input, T[lang].errors.phone);
    return ok;
  }

  function validatePreferredLanguage() {
    const input = fields.preferred_language;
    const lang = getCurrentLang();
    const ok = input.value !== '';
    ok ? clearError(input) : showError(input, T[lang].errors.preferred_language);
    return ok;
  }

  function validatePreferredClinic() {
    const input = fields.preferred_clinic;
    const lang = getCurrentLang();
    const ok = input.value !== '';
    ok ? clearError(input) : showError(input, T[lang].errors.preferred_clinic);
    updateEveningWarning();
    return ok;
  }

  function validatePreferredDate() {
    const input = fields.preferred_date;
    const lang = getCurrentLang();
    let ok = false;
    if (input.value) {
      const selected = new Date(input.value + 'T00:00:00');
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const minDate = addBusinessDays(today, 1);
      const maxDate = new Date(today);
      maxDate.setDate(maxDate.getDate() + 60);
      ok = selected >= minDate && selected <= maxDate;
    }
    ok ? clearError(input) : showError(input, T[lang].errors.preferred_date);
    return ok;
  }

  function validatePreferredTime() {
    const input = fields.preferred_time;
    const lang = getCurrentLang();
    const ok = input.value !== '';
    ok ? clearError(input) : showError(input, T[lang].errors.preferred_time);
    updateEveningWarning();
    return ok;
  }

  function validateServiceType() {
    const input = fields.service_type;
    const lang = getCurrentLang();
    const ok = input.value !== '';
    ok ? clearError(input) : showError(input, T[lang].errors.service_type);
    validatePaediatricCrossCheck();
    return ok;
  }

  function validatePaediatricCrossCheck() {
    const lang = getCurrentLang();
    const serviceInput = fields.service_type;
    if (serviceInput.value !== 'paediatric') return true;
    if (!fields.date_of_birth.value) return true; // DOB error already owns that field
    const dob = new Date(fields.date_of_birth.value + 'T00:00:00');
    const age = calculateAge(dob, new Date());
    const ok = age < 18;
    if (!ok) {
      showError(serviceInput, T[lang].errors.service_type_paediatric);
    } else if (serviceInput.value !== '') {
      clearError(serviceInput);
    }
    return ok;
  }

  function updateEveningWarning() {
    const time = fields.preferred_time.value;
    const clinic = fields.preferred_clinic.value;
    const closesBefore8 = clinic && CLINIC_EVENING_CLOSE[clinic] && CLINIC_EVENING_CLOSE[clinic] < 20;
    eveningWarning.classList.toggle('hidden', !(time === 'evening' && closesBefore8));
  }

  function validateNewPatient() {
    const lang = getCurrentLang();
    const value = getRadioValue('new_patient');
    const ok = value !== '';
    ok ? clearGroupError('new_patient-error') : showGroupError('new_patient-error', T[lang].errors.new_patient);

    const showPatientId = value === 'no';
    patientIdWrapper.classList.toggle('hidden', !showPatientId);
    if (!showPatientId) {
      fields.patient_id.value = '';
      clearError(fields.patient_id);
    }
    return ok;
  }

  function validatePatientId() {
    const input = fields.patient_id;
    const lang = getCurrentLang();
    if (patientIdWrapper.classList.contains('hidden') || input.value.trim() === '') {
      clearError(input);
      return true; // optional field
    }
    const ok = /^HC-[A-Za-z0-9]{6}$/.test(input.value.trim());
    ok ? clearError(input) : showError(input, T[lang].errors.patient_id);
    return ok;
  }

  function validateHasInsurance() {
    const lang = getCurrentLang();
    const value = getRadioValue('has_insurance');
    const ok = value !== '';
    ok ? clearGroupError('has_insurance-error') : showGroupError('has_insurance-error', T[lang].errors.has_insurance);

    const showInsurance = value === 'yes';
    insuranceWrapper.classList.toggle('hidden', !showInsurance);
    fields.insurance_provider.required = showInsurance;
    fields.insurance_member_id.required = showInsurance;
    if (!showInsurance) {
      fields.insurance_provider.value = '';
      fields.insurance_member_id.value = '';
      clearError(fields.insurance_provider);
      clearError(fields.insurance_member_id);
    }
    return ok;
  }

  function validateInsuranceProvider() {
    const input = fields.insurance_provider;
    const lang = getCurrentLang();
    if (!input.required) {
      clearError(input);
      return true;
    }
    const ok = input.value.trim() !== '' && input.value.trim().length <= 100;
    ok ? clearError(input) : showError(input, T[lang].errors.insurance_provider);
    return ok;
  }

  function validateInsuranceMemberId() {
    const input = fields.insurance_member_id;
    const lang = getCurrentLang();
    if (!input.required) {
      clearError(input);
      return true;
    }
    const ok = /^[A-Za-z0-9]{6,20}$/.test(input.value.trim());
    ok ? clearError(input) : showError(input, T[lang].errors.insurance_member_id);
    return ok;
  }

  function updateHealthConcernCounter() {
    const lang = getCurrentLang();
    const len = fields.health_concern.value.length;
    healthConcernCounter.textContent = T[lang].counter(len);
    healthConcernCounter.classList.toggle('text-red-600', len < 20);
    healthConcernCounter.classList.toggle('text-slate-500', len >= 20);
  }

  function validateHealthConcern() {
    const input = fields.health_concern;
    const lang = getCurrentLang();
    const len = input.value.trim().length;
    const ok = len >= 20 && len <= 500;
    if (ok) {
      clearError(input);
    } else {
      const remaining = Math.max(0, 20 - len);
      showError(input, T[lang].healthConcernError(remaining));
    }
    updateHealthConcernCounter();
    return ok;
  }

  function validateConsent() {
    const input = fields.contact_consent;
    const lang = getCurrentLang();
    const ok = input.checked;
    ok ? clearError(input) : showError(input, T[lang].errors.contact_consent);
    return ok;
  }

  /* Re-render whatever error/counter text is currently visible when the
     visitor flips the language toggle mid-form. */
  function refreshDynamicText() {
    const lang = getCurrentLang();
    updateHealthConcernCounter();
    if (fields.health_concern.getAttribute('aria-invalid') === 'true') validateHealthConcern();
    Object.values(fields).forEach((input) => {
      if (input && input.getAttribute && input.getAttribute('aria-invalid') === 'true') {
        // Re-run that field's own validator to refresh its message in the new language.
        const validators = {
          first_name: validateFirstName, last_name: validateLastName,
          date_of_birth: validateDateOfBirth, email: validateEmail, phone: validatePhone,
          preferred_language: validatePreferredLanguage, preferred_clinic: validatePreferredClinic,
          preferred_date: validatePreferredDate, preferred_time: validatePreferredTime,
          service_type: validateServiceType, insurance_provider: validateInsuranceProvider,
          insurance_member_id: validateInsuranceMemberId, patient_id: validatePatientId,
          contact_consent: validateConsent
        };
        if (validators[input.id]) validators[input.id]();
      }
    });
    if (!document.getElementById('new_patient-error').classList.contains('hidden')) {
      showGroupError('new_patient-error', T[lang].errors.new_patient);
    }
    if (!document.getElementById('has_insurance-error').classList.contains('hidden')) {
      showGroupError('has_insurance-error', T[lang].errors.has_insurance);
    }
  }
  window.refreshDynamicText = refreshDynamicText;

  /* ---------- Event wiring — blur/change for validation, input for the live counter (§1.9, §3.1) ---------- */
  fields.first_name.addEventListener('blur', validateFirstName);
  fields.last_name.addEventListener('blur', validateLastName);
  fields.date_of_birth.addEventListener('blur', validateDateOfBirth);
  fields.date_of_birth.addEventListener('change', validateDateOfBirth);
  fields.email.addEventListener('blur', validateEmail);
  fields.phone.addEventListener('blur', validatePhone);
  fields.preferred_language.addEventListener('change', validatePreferredLanguage);
  fields.preferred_clinic.addEventListener('change', validatePreferredClinic);
  fields.preferred_date.addEventListener('change', validatePreferredDate);
  fields.preferred_time.addEventListener('change', validatePreferredTime);
  fields.service_type.addEventListener('change', validateServiceType);
  fields.insurance_provider.addEventListener('blur', validateInsuranceProvider);
  fields.insurance_member_id.addEventListener('blur', validateInsuranceMemberId);
  fields.patient_id.addEventListener('blur', validatePatientId);
  fields.contact_consent.addEventListener('change', validateConsent);

  form.querySelectorAll('input[name="new_patient"]').forEach((r) => r.addEventListener('change', validateNewPatient));
  form.querySelectorAll('input[name="has_insurance"]').forEach((r) => r.addEventListener('change', validateHasInsurance));

  fields.health_concern.addEventListener('input', updateHealthConcernCounter); // live counter — every keystroke, by design
  fields.health_concern.addEventListener('blur', validateHealthConcern);

  updateHealthConcernCounter(); // initialize counter at 0

  /* ---------- Submit: validate everything, block on any failure, show success on pass (§1.18, §3.8) ---------- */
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const results = [
      validateFirstName(), validateLastName(), validateDateOfBirth(),
      validateEmail(), validatePhone(), validatePreferredLanguage(),
      validatePreferredClinic(), validatePreferredDate(), validatePreferredTime(),
      validateServiceType(), validatePaediatricCrossCheck(),
      validateNewPatient(), validatePatientId(),
      validateHasInsurance(), validateInsuranceProvider(), validateInsuranceMemberId(),
      validateHealthConcern(), validateConsent()
    ];

    const allValid = results.every(Boolean);

    if (allValid) {
      form.hidden = true;
      successMessage.classList.remove('hidden');
      successMessage.focus();
      successMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      const firstInvalid = form.querySelector('[aria-invalid="true"]') ||
        form.querySelector('.border-red-500');
      if (firstInvalid) firstInvalid.focus();
    }
  });

  /* ---------- Clear form: wipe values AND every custom error/visibility state (§5.7) ---------- */
  form.addEventListener('reset', () => {
    setTimeout(() => {
      Object.values(fields).forEach((input) => {
        if (input) clearError(input);
      });
      clearGroupError('new_patient-error');
      clearGroupError('has_insurance-error');
      patientIdWrapper.classList.add('hidden');
      insuranceWrapper.classList.add('hidden');
      eveningWarning.classList.add('hidden');
      fields.insurance_provider.required = false;
      fields.insurance_member_id.required = false;
      updateHealthConcernCounter();
      successMessage.classList.add('hidden');
      form.hidden = false;
    }, 0);
  });
}); 
