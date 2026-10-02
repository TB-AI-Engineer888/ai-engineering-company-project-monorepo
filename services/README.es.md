# Carpeta `services`

Esta carpeta contiene **todos los servicios backend** (APIs y workers en segundo plano) relacionados con la compañía para el proyecto transversal de AI Engineering.

Cada subcarpeta dentro de `services/` debe corresponder a **un servicio concreto** (por ejemplo `admin-api`, `data-processor-worker`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar toda la lógica backend, APIs y consumidores de colas que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) los servicios que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlos.

## API de cuenta

`services/api` ofrece el restablecimiento y el cambio de contraseña de las cuentas de HealthCore.

Define estas variables en un archivo `.env` en la raíz del repositorio. No subas `.env`. Los nombres están en `services/api/.env.example`.

- `RESEND_API_KEY` — clave de Resend usada para enviar el correo de restablecimiento.
- `RESEND_FROM` — dirección del remitente. `HealthCore <onboarding@resend.dev>` sirve antes de verificar un dominio propio.
- `APP_URL` — origen de la interfaz que va en el enlace. Valor local: `http://127.0.0.1:43123`.

Ejecuta la API con `python services/api/run.py` (puerto 43180). Ejecuta el backoffice desde `uis/backoffice` (puerto 43123).
