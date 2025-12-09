# Configuración de Envío de Correos Electrónicos

## ✅ Sistema Implementado

Se ha implementado un sistema completo de notificaciones por correo electrónico que incluye:

### 📧 Emails Implementados

1. **Cronograma Detallado de Préstamo** (al crear el préstamo)
   - Resumen del préstamo (monto, TEA, plazo, fechas)
   - Tabla HTML completa con todas las cuotas
   - Desglose de capital, interés y saldo
   - Identificación de cuotas de ajuste
   - PDF adjunto con cronograma detallado

2. **Voucher de Pago** (al registrar cada cuota)
   - Confirmación de pago exitoso
   - Datos del cliente y préstamo
   - Detalle financiero (capital, interés, total)
   - Método de pago utilizado
   - Conciliación contable (si hay ajuste por redondeo Ley 29571)
   - Estado del préstamo y próxima cuota
   - PDF adjunto con voucher/comprobante

### 📂 Archivos Creados/Modificados

**Templates HTML:**
- `app/templates/emails/cronograma_detallado.html` - Email con cronograma completo
- `app/templates/emails/voucher_pago.html` - Email con comprobante de pago

**Servicios:**
- `app/services/email_service.py`:
  - `enviar_cronograma_completo()` - Nuevo método para cronograma detallado
  - `enviar_voucher_pago()` - Nuevo método para vouchers de pago
  
- `app/services/pdf_service.py`:
  - `generar_voucher_pago()` - Genera PDF del comprobante de pago

- `app/services/pago_service.py`:
  - Integrado envío automático de voucher al registrar pago (línea ~268)

- `app/services/prestamo_service.py`:
  - Actualizado para usar `enviar_cronograma_completo()` (línea ~277)

---

## 🔧 Configuración de Gmail

Para que el sistema pueda enviar correos electrónicos reales, necesitas configurar las credenciales de Gmail.

### Paso 1: Generar App Password de Gmail

1. **Habilitar verificación en 2 pasos:**
   - Ve a tu cuenta de Google: https://myaccount.google.com/
   - Seguridad → Verificación en 2 pasos
   - Actívala si no lo has hecho

2. **Generar contraseña de aplicación:**
   - Ve a: https://myaccount.google.com/apppasswords
   - En "Seleccionar app" → Correo
   - En "Seleccionar dispositivo" → Otro (nombre personalizado)
   - Escribe: "Financiera Demo - App Flask"
   - Clic en "Generar"
   - **Copia la contraseña de 16 caracteres** (sin espacios)

### Paso 2: Actualizar Variables de Entorno

Edita el archivo `.env` en la raíz del proyecto:

```bash
# Configuración de Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=example@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx    # ⚠️ REEMPLAZAR con tu App Password
MAIL_DEFAULT_SENDER=example@gmail.com

# Para pruebas: imprime en consola sin enviar
# Para producción: comenta o cambia a False
common/config.py
MAIL_DEBUG=True
```

**Importante:** 
- Reemplaza `xxxx xxxx xxxx xxxx` con la contraseña de aplicación de 16 caracteres que generaste
- El App Password tiene el formato: `abcd efgh ijkl mnop` (4 grupos de 4 letras)
- **NO uses tu contraseña normal de Gmail**, usa el App Password

### Paso 3: Reiniciar la Aplicación

Después de actualizar el `.env`, reinicia el servidor Flask para que tome los nuevos valores:

```powershell
# Si está corriendo, detenerlo (Ctrl+C)
# Luego reiniciar:
.\env\Scripts\Activate.ps1
python app.py
```

---

## 🧪 Probar el Envío de Emails

### Opción 1: Ejecutar el Test Completo

```powershell
.\env\Scripts\Activate.ps1
python .\tests\test_pago_completo.py
```

Este test:
- ✅ Crea un préstamo → **Envía cronograma detallado**
- ✅ Registra 3 pagos → **Envía 3 vouchers de pago**

### Opción 2: Modo Debug (sin enviar emails reales)

Si quieres probar sin enviar emails, mantén en `.env`:

```bash
MAIL_DEBUG=True
```

Esto imprimirá los emails en la consola en lugar de enviarlos.

### Opción 3: Usar el Endpoint de API

Puedes crear un préstamo vía POST request:

```bash
POST http://localhost:5000/api/prestamos
Content-Type: application/json

{
    "dni": "12345678",
    "correo_electronico": "tu_email@gmail.com",
    "monto_total": 1000,
    "interes_tea": 10,
    "plazo": 3,
    "f_otorgamiento": "2025-12-08"
}
```

Y registrar pagos:

```bash
POST http://localhost:5000/api/pagos
Content-Type: application/json

{
    "prestamo_id": 1,
    "cuota_id": 1,
    "metodo_pago": "EFECTIVO"
}
```

