# SOP - Operador de Lotes AMB

## Objetivo
Establecer el procedimiento operativo estándar para la gestión de lotes en el sistema AMB (Advanced Manufacturing Batch).

## Alcance
Este SOP aplica a todos los operadores de lotes que trabajan con el módulo Batch AMB en el sistema.

## Procedimiento

### 1. Creación de Lote Nivel 1 (Lote Principal)

1. Iniciar sesión en el sistema
2. Navegar a: **Batch AMB > Nuevo**
3. Completar los campos obligatorios:
   - **Item a Manufacture**: Seleccionar el producto
   - **Nivel de Lote**: "1" (Lote Principal)
   - **Cantidad Planeada**: Ingresar la cantidad a producir
4. El sistema generará automáticamente el título del lote
5. Guardar en estado "Borrador"

### 2. Creación de Lote Nivel 2 (Sub-lote)

1. Desde el Lote Nivel 1 creado, hacer clic en **Crear Sub-lote**
2. El sistema creará automáticamente un Lote Nivel 2 vinculado
3. Verificar que el campo **parent_batch_amb** apunte al Lote Nivel 1
4. Completar cantidad planeada para el sub-lote
5. Guardar en estado "Borrador"

### 3. Creación de Lote Nivel 3 (Contenedor)

1. Desde el Lote Nivel 2, hacer clic en **Crear Contenedor**
2. El sistema creará automáticamente un Lote Nivel 3 vinculado
3. Verificar que el título siga la jerarquía: `LOTE_PADRE-SUBLON-C1`
4. Guardar en estado "Borrador"

### 4. Generación de Números de Serie

1. Seleccionar el Lote Nivel 3 (Contenedor)
2. Hacer clic en **Generar Seriales de Barril**
3. Ingresar la cantidad de contenedores a generar
4. El sistema generará los seriales en formato: `TÍTULO-001`, `TÍTULO-002`, etc.
   - Ejemplo: `JAR0001261-1-C1-001`

### 5. Gestión de Estados del Pipeline

| Estado | Descripción | Transición Permitida |
|--------|-------------|---------------------|
| Borrador | Lote creado, sin procesar | → WO Vinculado |
| WO Vinculado | Orden de trabajo asociada | → En Proceso |
| En Proceso | Producción iniciada | → Control Calidad |
| Control Calidad | En verificación | → Completado |
| Completado | Producción finalizada | - |

### 6. Registro de Peso de Contenedores

1. En el Lote Nivel 3, ir a la tabla **Barriles/Contenedores**
2. Para cada contenedor:
   - Ingresar **Peso Bruto**
   - Ingresar **Peso Tara**
   - El sistema calculará automáticamente el peso neto
3. Validar pesos haciendo clic en **Validar Peso**

## Validaciones

- El campo `work_order_ref` es obligatorio para todos los niveles
- La cantidad planeada debe ser mayor a 0
- Los seriales deben cumplir con formato CODE-39

## Referencias
- Documento: SOP Inspector Calidad
- Documento: Guía Gerente Producción
