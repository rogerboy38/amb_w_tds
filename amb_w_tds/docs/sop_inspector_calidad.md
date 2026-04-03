# SOP - Inspector de Calidad AMB

## Objetivo
Establecer el procedimiento de inspección de calidad para lotes AMB durante el proceso de producción y empaque.

## Alcance
Este SOP aplica a inspectores de calidad que verifican lotes en el sistema AMB.

## Responsabilidades

- Verificar pesos de contenedores
- Validar seriales generados
- Confirmar estados del pipeline
- Registrar resultados de inspección

## Procedimiento de Inspección

### 1. Recepción de Lote para Inspección

1. Recibir notificación de lote en estado "Control Calidad"
2. Acceder al Lote Nivel 3 correspondiente
3. Revisar historial de producción

### 2. Verificación de Pesos

1. Acceder a la tabla **Barriles/Contenedores**
2. Para cada contenedor:
   - Verificar Peso Bruto registrado
   - Verificar Peso Tara registrado
   - Calcular Peso Neto = Bruto - Tara
3. Comparar con especificaciones del producto

**Criterios de Aceptación:**
| Campo | Requisito |
|-------|-----------|
| Peso Neto | Dentro de tolerancia ±2% |
| Serial | Formato CODE-39 válido |
| Estado | "Validado" marcado |

### 3. Validación de Seriales

1. Verificar que los seriales cumplan el formato:
   - `TÍTULO-001` a `TÍTULO-999`
2. Confirmar que no hay seriales duplicados
3. Verificar que el formato no contenga prefijos redundantes

### 4. Inspección Visual

- Verificar que los barriletes estén correctamente etiquetados
- Confirmar que el código de barras sea legible
- Verificar estado de integridad física

### 5. Registro de Resultados

1. En el documento Batch AMB:
   - Marcar **weight_validated** = 1 para cada contenedor aprobado
   - Agregar notas de inspección en campo comentarios
2. Actualizar estado del pipeline si todo está conforme

### 6. No Conformidades

Si se detectan no conformidades:

1. Documentar el problema en el campo de notas
2. Cambiar estado del pipeline a "Borrador" para corrección
3. Notificar al operador de lotes responsable

##bitulacion

| Aspecto | Estado Final |
|---------|--------------|
| Pesos validados | Todos marcados |
| Seriales verificados | Formato correcto |
| Inspección visual | Aprobada |
| Pipeline | Completado o en corrección |

## Referencias
- Documento: SOP Operador de Lotes
- Documento: Guía Gerente Producción
