# Guía - Gerente de Producción AMB

## Objetivo
Proporcionar guía estratégica para gerentes de producción sobre la gestión de lotes AMB y monitoreo del proceso productivo.

## Alcance
Esta guía aplica a gerentes de producción que supervisan operaciones de manufactura usando el sistema AMB.

## Responsabilidades del Gerente

- Monitorear estados de lotes
- Analizar métricas de producción
- Optimizar flujos de trabajo
- Gestionar transiciones de pipeline

## Dashboard de Producción

### Métricas Clave

| Métrica | Descripción | Umbral |
|---------|-------------|--------|
| Lotes Activos | Total de lotes en proceso | Según capacidad |
| Eficiencia | Lotes completados vs planeados | > 90% |
| Tiempo Promedio | Días promedio por nivel | < 5 días |
| No Conformidades | Lotes con problemas | < 5% |

### Monitoreo de Estados

1. **Borrador**: Lotes nuevos sin iniciar
2. **WO Vinculado**: Con orden de trabajo asignada
3. **En Proceso**: Producción activa
4. **Control Calidad**: En verificación QA
5. **Completado**: Producción finalizada

## Gestión de Capacidad

### Por Nivel

| Nivel | Capacidad Típica | Uso |
|-------|-----------------|-----|
| L1 (Principal) | Según pedido | 1 por orden |
| L2 (Sub-lote) | 1-10 por L1 | División lógica |
| L3 (Contenedor) | 1-100 por L2 | Unidades físicas |

### Planeación de Capacidad

1. Revisar órdenes de trabajo pendientes
2. Asignar recursos a lotes activos
3. Monitorear bottlenecks en producción

## Control de Calidad

### Procesos de Verificación

- Revisar Pesos de contenedores (tolerancia ±2%)
- Validar Seriales (formato CODE-39)
- Confirmar Integridad de etiquetas

### Indicadores de Calidad

- Tasa de aprobación primera vez: > 95%
- Error en seriales: < 1%
- Discrepancias de peso: < 3%

## Integración con Otros Módulos

### Work Orders

- Cada Lote Nivel 1 debe tener WO vinculada
- El sistema sincroniza cantidad planeada automáticamente

### Lote AMB

- El sistema crea registro Lote AMB al completar lote
- Sincroniza estados y métricas

### Stock Entries

- Al enviar lote, se crea Stock Entry automático
- Registra inventario en almacén destinatario

## Informes y Análisis

### Reportes Disponibles

1. **Estado de Lotes**: Vista general de todos los lotes
2. **Historial de Seriales**: Trazabilidad de seriales generados
3. **Métricas de Producción**: KPIs de rendimiento
4. **No Conformidades**: Lista de problemas detectados

### Exportación

- Los reportes pueden exportarse a Excel
- Programar envios automáticos por correo

## Referencias
- Documento: SOP Operador de Lotes
- Documento: SOP Inspector Calidad
