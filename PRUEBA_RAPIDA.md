# ✅ PRUEBA RÁPIDA - API funcionando

## 🎉 **Problema resuelto:**
1. ✅ Tablas creadas en la BD (ejecutamos `flask db upgrade`)
2. ✅ 5 clientes de prueba insertados
3. ✅ Endpoint `/api/v1/clientes/dni/{dni}` funcionando
4. ✅ JavaScript corregido para usar el endpoint correcto
5. ✅ Modelo actualizado para incluir campo `id`

---

## 🧪 **DNIs de prueba disponibles:**

| DNI | Nombre | Estado PEP |
|-----|--------|------------|
| **12345678** | Juan Carlos Pérez García | 🟢 Normal |
| **87654321** | María Elena Torres Rojas | 🔴 PEP |
| **11223344** | Pedro Pablo Kucinski López | 🟢 Normal |
| **44332211** | Ana Sofía Ramírez Mendoza | 🟢 Normal |
| **55667788** | Carlos Alberto Sánchez Vargas | 🔴 PEP |

---

## 📋 **Pasos para probar:**

### 1. **Asegúrate que el servidor esté corriendo:**
```powershell
python app.py
```
Deberías ver: `* Running on http://127.0.0.1:5000`

### 2. **Abre el navegador:**
```
http://localhost:5000/buscar
```

### 3. **Prueba buscar un cliente:**
- Ingresa DNI: `12345678`
- Click en "Buscar"
- ✅ Deberías ver: "Cliente encontrado"
- ✅ Los campos se llenan automáticamente con los datos del cliente

### 4. **Prueba un cliente PEP:**
- Ingresa DNI: `87654321`
- Click en "Buscar"
- ✅ Deberías ver el aviso PEP en amarillo

### 5. **Crea un préstamo:**
- Después de buscar un cliente
- Ingresa Monto: `5000`
- Ingresa Cuotas: `6`
- Click en "Guardar Cambios"
- ✅ Deberías ver el modal de confirmación

---

## 🔍 **Debug en consola del navegador (F12):**

Deberías ver estos logs:
```
client-search.js loaded
loan-modal.js loaded
Cliente encontrado  (cuando buscas un DNI)
saveLoanChanges called  (cuando guardas un préstamo)
```

---

## 🧪 **Probar API directamente con curl:**

### Listar todos los clientes:
```powershell
curl http://localhost:5000/api/v1/clientes
```

### Buscar por DNI:
```powershell
curl http://localhost:5000/api/v1/clientes/dni/12345678
```

### Respuesta esperada:
```json
{
  "id": 1,
  "cliente_id": 1,
  "dni": "12345678",
  "nombre_completo": "Juan Carlos",
  "apellido_paterno": "Pérez",
  "apellido_materno": "García",
  "pep": false,
  "fecha_registro": "2025-10-15T..."
}
```

---

## ⚠️ **Si aún no funciona:**

1. **Reinicia el servidor Flask:**
   - Ctrl+C en la terminal donde corre `python app.py`
   - Ejecuta nuevamente: `python app.py`

2. **Limpia caché del navegador:**
   - Ctrl+Shift+R (recarga forzada)
   - O abre en modo incógnito

3. **Verifica la consola del navegador (F12):**
   - Pestaña "Console" para ver errores JavaScript
   - Pestaña "Network" para ver las peticiones HTTP

4. **Verifica que la BD tenga datos:**
   ```powershell
   python test_api.py
   ```

---

## 🎯 **Próximos pasos:**

Una vez que la búsqueda funcione:
- ✅ Implementar guardado real de préstamos (endpoint `/api/v1/prestamos`)
- ✅ Conectar con la API de RENIEC para DNIs nuevos
- ✅ Agregar validaciones adicionales
