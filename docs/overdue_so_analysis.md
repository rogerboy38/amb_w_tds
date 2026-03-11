# Análisis Integral: Gestión de Órdenes de Venta Vencidas en ERPNext Provenientes de Migración de Datos

## Resumen Ejecutivo

El presente informe aborda de manera exhaustiva la problemática de las órdenes de venta vencidas en ERPNext, específicamente aquellas provenientes de procesos de migración de datos desde sistemas legacy. El análisis se fundamenta en los datos proporcionados por el usuario, que identifican ocho órdenes de venta con estado vencido, cuyo valor total representa un importe significativo para la operación de la empresa.

La gestión inadecuada de estos registros históricos puede generar múltiples complicaciones operativas, incluyendo distorsiones en los indicadores de rendimiento, dificultades en la generación de reportes financieros y problemas de integridad en la trazabilidad del sistema. Por ello, este documento proporciona un análisis detallado de las opciones disponibles en ERPNext para procesar estas órdenes, acompañado de mejores prácticas especializadas para datos de migración y un plan de acción concreto con comandos específicos para su implementación.

El informe está estructurado para proporcionar tanto la comprensión conceptual de las herramientas disponibles en ERPNext, como las instrucciones técnicas necesarias para ejecutar las acciones recomendadas de manera segura y eficiente.

---

## 1. Introducción y Contexto

### 1.1 Antecedentes del Problema

Los procesos de migración de datos representan uno de los desafíos más significativos en la implementación de sistemas ERP como ERPNext. Durante la migración desde sistemas legacy, es común encontrar registros históricos que, por diversas circunstancias, quedan en estados inconsistentes o pendientes de resolución. Las órdenes de venta vencidas constituyen uno de los casos más frecuentes y problemáticos, ya que representan compromisos comerciales que, por alguna razón, no fueron completados en los plazos establecidos.

En el contexto específico de la implementación de ERPNext para AMB-Wellness, se ha identificado la presencia de órdenes de venta vencidas que requieren atención inmediata. Estos registros no solo afectan la integridad de los datos del sistema, sino que también pueden generar confusión en los equipos de ventas, logística y finanzas, además de distorsionar los indicadores clave de rendimiento del negocio.

### 1.2 Alcance del Análisis

Este informe comprende el análisis de ocho órdenes de venta identificadas como vencidas, con un enfoque particular en tres de ellas que han sido específicamente documentadas por el usuario. Adicionalmente, se examinan las opciones nativas de ERPNext para la gestión de órdenes en estados problemáticos, se establecen mejores prácticas para el manejo de datos de migración antiguos y se propone un plan de acción detallado con comandos específicos para cada escenario.

La información presentada en este documento es aplicable a entornos ERPNext versión 14 o superior, que corresponde a las versiones actualmente mantenidas y utilizadas en la implementación de AMB-Wellness.

---

## 2. Análisis de las Órdenes de Venta Vencidas

### 2.1 Identificación y Caracterización de los Registros Affectedos

Las órdenes de venta vencidas identificadas en el sistema corresponden a transacciones que han superado su fecha de entrega programada sin que se haya completado el proceso de despacho o facturación. A continuación se presenta el detalle de los tres registros específicamente documentados, seguidos del contexto general de los cinco adicionales.

La primera orden de venta identificada corresponde a **SO-117326-AGROMAYAL BOTÁNICA**, con un valor total de **$11,218,680.00 MXN** y fecha de entrega programada para el **13 de febrero de 2026**. Este registro representa el importe más significativo entre todas las órdenes vencidas identificadas, lo cual indica que requiere atención prioritaria debido al impacto financiero que podría tener en las operaciones de la empresa. La fecha de vencimiento superando el mes de febrero de 2026 sugiere que esta orden ha permanecido en estado pendiente por un período considerable, lo cual incrementa la probabilidad de que los compromisos comerciales asociados requieran revisión o actualización.

El segundo registro documentado es **SO-117026-BARENTZ Service S.p.A.**, por un valor de **$771.21 MXN** con fecha de entrega del **7 de febrero de 2026**. Aunque el importe de esta orden es considerablemente menor que el anterior, su identificación como vencida no debe minimizar su importancia, ya que podría representar una relación comercial activa que requiere seguimiento para evitar afectar la percepción del cliente sobre la capacidad de ejecución de la empresa.

El tercer registro corresponde a **SO-116926-LORAND LABORATORIES LLC**, con un valor de **$116,844.92 MXN** y fecha de entrega del **7 de febrero de 2026**. Este cliente ya ha sido documentado en el sistema con una orden de venta activa (SO-00763) que presenta compromisos de entrega para julio de 2026, lo cual sugiere una relación comercial activa que podría verse afectada por inconsistencias en los registros históricos.

### 2.2 Tabla Consolidada de Órdenes Vencidas

A continuación se presenta una tabla que consolida la información de las órdenes de venta vencidas identificadas, incluyendo las tres específicamente documentadas y el contexto de las cinco adicionales mencionadas por el usuario:

| Número de Orden | Cliente | Valor (MXN) | Fecha de Entrega | Estado |
|-----------------|---------|--------------|------------------|--------|
| SO-117326 | AGROMAYAL BOTÁNICA | $11,218,680.00 | 13/02/2026 | Vencida |
| SO-117026 | BARENTZ Service S.p.A. | $771.21 | 07/02/2026 | Vencida |
| SO-116926 | LORAND LABORATORIES LLC | $116,844.92 | 07/02/2026 | Vencida |
| SO-XXXXX | Cliente no especificado 1 | Por determinar | Por determinar | Vencida |
| SO-XXXXX | Cliente no especificado 2 | Por determinar | Por determinar | Vencida |
| SO-XXXXX | Cliente no especificado 3 | Por determinar | Por determinar | Vencida |
| SO-XXXXX | Cliente no especificado 4 | Por determinar | Por determinar | Vencida |
| SO-XXXXX | Cliente no especificado 5 | Por determinar | Por determinar | Vencida |

### 2.3 Implicaciones del Estado Vencido

Las órdenes de venta en estado vencido generan múltiples implicaciones para la operación del negocio. Desde la perspectiva financiera, estos registros infl artificialmente los saldos de cuentas por cobrar pendientes y distorsionan los indicadores de rotación de inventario y antigüedad de cartera. Desde el punto de vista operativo, los equipos de ventas y logística pueden experimentar confusión al consultar pedidos que técnicamente deberían haber sido completados, lo cual dificulta la planificación de capacidades y la asignación de recursos.

Adicionalmente, en el contexto de datos migrados, las órdenes vencidas pueden representar situaciones diversas que requieren tratamiento diferenciado. Algunas posibilidades incluyen pedidos que efectivamente fueron entregados fuera del sistema y nunca se actualizó su estado, pedidos cancelados verbalmente sin la documentación correspondiente, pedidos que esperan confirmación del cliente, o pedidos que fueron reabiertos para atención especial y posteriormente abandonados.

---

## 3. Opciones de ERPNext para la Gestión de Órdenes Vencidas

### 3.1 Cerrar Orden de Venta (Close Sales Order)

La opción de cerrar una orden de venta en ERPNext representa la acción menos destructiva disponible para gestionar registros problemáticos. Cuando se cierra una orden de venta, el sistema mantiene el registro completo en la base de datos pero marca el documento como cerrado, lo cual tiene varias implicaciones importantes que deben comprenderse antes de ejecutar esta acción.

El cierre de una orden de venta en ERPNext se realiza mediante el campo de estado "Status" que puede modificarse desde la interfaz del documento. Para ejecutar esta acción a través de la consola de Frappe, se puede utilizar el siguiente código que permite cerrar múltiples órdenes de forma masiva:

```
# Script para cerrar órdenes de venta vencidas
import frappe

# Lista de órdenes a cerrar
ordenes = [
    "SO-117326-AGROMAYAL BOTÁNICA",
    "SO-117026-BARENTZ Service S.p.A.",
    "SO-116926-LORAND LABORATORIES LLC"
]

for orden in ordenes:
    try:
        so = frappe.get_doc("Sales Order", orden)
        if so.status not in ["Closed", "Cancelled", "Completed"]:
            so.status = "Closed"
            so.flags.ignore_permissions = True
            so.save()
            frappe.db.commit()
            print(f"Orden {orden} cerrada exitosamente")
        else:
            print(f"Orden {orden} ya se encuentra en estado: {so.status}")
    except Exception as e:
        print(f"Error al procesar {orden}: {str(e)}")
```

Esta opción es particularmente recomendable cuando se desea preservar la trazabilidad histórica del pedido, incluyendo los compromisos de entrega, las notas del cliente y cualquier comunicación asociada. El registro cerrado continuará apareciendo en búsquedas y reportes, pero no permitirá la creación de notas de entrega o facturas adicionales basadas en esta orden.

### 3.2 Detener Orden de Venta (Stop Sales Order)

La opción de detener una orden de venta en ERPNext se utiliza principalmente cuando existe la intención de completar parcialmente el pedido o cuando se requiere suspender temporalmente el procesamiento mientras se resuelve alguna situación específica con el cliente. El estado "Stopped" indica que el procesamiento de la orden ha sido interrumpido, pero el registro permanece activo en el sistema.

Para detener una orden de venta, ERPNext proporciona una funcionalidad específica que permite indicar las cantidades que han sido despachadas hasta el momento de la interrupción. Esta característica resulta especialmente útil cuando se han realizado despachos parciales y se necesita registrar formalmente la suspensión del resto del compromiso. El comando para ejecutar esta acción mediante la consola de Bench es:

```
# Detener una orden de venta específica
bench execute frappe.client.set_value --kwargs '{"doctype": "Sales Order", "name": "SO-117326-AGROMAYAL BOTÁNICA", "fieldname": "status", "value": "Stopped"}'
```

Es importante destacar que una orden detenida puede ser reactivada posteriormente si las circunstancias cambian, a diferencia de las opciones de cancelación que implican una acción más definitiva. Sin embargo, el estado detenido también impide la creación de nuevas notas de entrega hasta que la orden sea reactivada.

### 3.3 Cancelar Orden de Venta (Cancel Sales Order)

La cancelación de una orden de venta en ERPNext representa la opción más drástica y debe utilizarse con extrema precaución, especialmente en el contexto de datos migrados. La cancelación elimina efectivamente el documento del flujo activo del sistema, aunque los registros permanecen en la base de datos con estado "Cancelled" para mantener la integridad de la auditoría.

Antes de cancelar una orden de venta, el sistema verifica que no existan notas de entrega o facturas asociadas que dependan de este documento. Si existen documentos relacionados, será necesario cancelarlos primero en orden inverso a su creación (primero facturas, luego notas de entrega). Esta verificación automática ayuda a prevenir inconsistencias en los datos, pero requiere un análisis cuidadoso antes de ejecutar la cancelación.

El proceso de cancelación debe realizarse siguiendo una secuencia específica para evitar dejar huérfanos en el sistema. A continuación se presenta el procedimiento recomendado:

```
# Procedimiento para cancelar una orden de venta con verificaciones previas
import frappe

def cancelar_orden_venta(nombre_orden):
    so = frappe.get_doc("Sales Order", nombre_orden)
    
    # Verificar estado actual
    if so.status in ["Cancelled", "Closed"]:
        print(f"La orden {nombre_orden} ya está cancelada o cerrada")
        return False
    
    # Verificar si existen notas de entrega asociadas
    delivery_notes = frappe.get_all(
        "Delivery Note",
        filters={"against_sales_order": nombre_orden},
        fields=["name", "docstatus"]
    )
    
    # Verificar si existen facturas asociadas
    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={"sales_order": nombre_orden},
        fields=["name", "docstatus"]
    )
    
    print(f"Notas de entrega asociadas: {len(delivery_notes)}")
    print(f"Facturas asociadas: {len(sales_invoices)}")
    
    if delivery_notes or sales_invoices:
        print("Advertencia: Existen documentos asociados. Cancele estos primero.")
        return False
    
    # Proceder con la cancelación
    try:
        so.cancel()
        frappe.db.commit()
        print(f"Orden {nombre_orden} cancelada exitosamente")
        return True
    except Exception as e:
        print(f"Error al cancelar: {str(e)}")
        frappe.db.rollback()
        return False

# Ejecución
cancelar_orden_venta("SO-117026-BARENTZ Service S.p.A.")
```

### 3.4 Comparativa de Opciones

La siguiente tabla presenta una comparación de las tres opciones disponibles para gestionar órdenes de venta vencidas, considerando factores como preservabilidad de datos, impacto en reportes, posibilidad de reversión y uso recomendado:

| Característica | Cerrar (Close) | Detener (Stop) | Cancelar (Cancel) |
|----------------|----------------|----------------|-------------------|
| Preservación de datos | Completa | Completa | Parcial (historial) |
| Reversible | Sí | Sí | No |
| Impacto en reportes | Moderado | Moderado | Bajo |
| Permite facturas | No | No | No |
| Recomendado para | Órdenes completadas | Suspensión temporal | Errores de migración |
| Riesgo de datos huérfanos | Bajo | Bajo | Alto |

---

## 4. Mejores Prácticas para Datos de Migración Antiguos

### 4.1 Principios Fundamentales

La gestión de datos provenientes de migraciones históricas requiere un enfoque diferenciado respecto a los datos operativos actuales. Los registros antiguos frecuentemente presentan inconsistencias que son normales en procesos de migración y no necesariamente indican problemas activos del negocio. Por ello, es fundamental establecer principios claros que guíen las decisiones sobre cómo procesar estos datos.

El primer principio fundamental es la **preservación de la trazabilidad**. Antes de realizar cualquier modificación o eliminación de registros históricos, debe asegurarse que la información relevante esté disponible en otros medios o que su eliminación no afecte la capacidad de auditoría de la organización. Los datos financieros迁移 siempre deben conservarse, incluso si requieren ser marcados de alguna forma especial para indicar su origen histórico.

El segundo principio es la **verificación de impacto**. Toda acción sobre datos de migración debe ser precedida por un análisis de qué otros registros podrían verse afectados. Las órdenes de venta pueden tener vinculadas notas de entrega, facturas, entradas de inventario, asientos contables y registros de pago que deben ser considerados antes de cualquier modificación.

El tercer principio es la **documentación de cambios**. Es recomendable mantener un registro de las modificaciones realizadas sobre datos históricos, incluyendo la justificación, la fecha de ejecución y el responsable. Esta documentación facilita futuras auditorías y ayuda a entender la evolución de los datos del sistema.

### 4.2 Estrategias de 处理 para Diferentes Escenarios

Las órdenes de venta vencidas provenientes de migración pueden clasificarse en diferentes categorías según su naturaleza, y cada categoría requiere un tratamiento específico. A continuación se presentan las estrategias recomendadas para cada escenario identificado.

**Órdenes completamente ejecutadas fuera del sistema**: Corresponden a pedidos que fueron atendidos mediante el sistema legacy pero cuyas notas de entrega y facturas no fueron registradas correctamente durante la migración. La recomendación en estos casos es crear los documentos de cumplimiento (notas de entrega y facturas) de forma retroactiva para mantener la trazabilidad completa, o en su defecto marcar las órdenes como cerradas indicando en un comentario que fueron ejecutadas manualmente.

**Órdenes canceladas verbalmente**: Representan pedidos que el cliente decidió no continuar pero que nunca fueron cancelados formalmente en el sistema legacy. Para estas órdenes, la opción recomendada es cancelarlas siempre que sea posible, verificando que no existan documentos dependientes. Si la cancelación no es viable debido a la antigüedad de los registros, se recomienda cerrarlas con un comentario explicativo.

**Órdenes pendientes legítimas**: Son pedidos que genuinamente esperan ejecución pero que, por diversas razones, no han sido procesados. Estas órdenes requieren revisión con el equipo comercial para determinar si el cliente aún tiene interés en el suministro, si existen condiciones pendientes por definir, o si la orden debe considerarse abandonada.

**Órdenes con errores de migración**: Corresponden a registros que nunca debieron existir o que contienen datos incorrectos debido a problemas en el proceso de migración. Estas órdenes pueden requerir cancelación si no existen documentos asociados, o en su defecto corrección de sus datos si la cancelación no es viable.

### 4.3 Recomendaciones Específicas para el Contexto de AMB-Wellness

Considerando el contexto específico de la implementación de ERPNext en AMB-Wellness y las características de los datos migrados identificadas, se proponen las siguientes recomendaciones específicas que deberían adoptarse como política de gestión de datos históricos.

Para las tres órdenes de venta específicamente documentadas en este análisis, la recomendación se estructura de la siguiente manera. Para **SO-117326-AGROMAYAL BOTÁNICA**, dado su alto valor ($11,218,680.00 MXN), se recomienda realizar una verificación activa con el cliente antes de tomar cualquier acción definitiva. Esta orden podría representar un compromiso comercial activo que requiere seguimiento directo con el equipo comercial para confirmar el estado actual de la relación con el cliente.

Para **SO-117026-BARENTZ Service S.p.A.**, con un valor relativamente bajo ($771.21 MXN), se recomienda evaluar si esta orden puede cerrarse directamente dado que el importe sugiere que podría tratarse de un pedido de muestra o demo que ya fue atendido por otros medios. Se sugiere revisar el historial del cliente en el sistema para confirmar.

Para **SO-116926-LORAND LABORATORIES LLC**, dado que existe una orden activa más reciente (SO-00763) con entrega programada para julio de 2026, se recomienda coordinar con el equipo comercial para confirmar si esta orden antigua debe cancelarse o si representa un compromiso separado que requiere atención.

Para las cinco órdenes adicionales no específicamente documentadas, se recomienda ejecutar un análisis masivo que permita clasificar cada registro en la categoría correspondiente antes de tomar acciones individuales.

---

## 5. Plan de Acción Recomendado

### 5.1 Fase 1: Análisis y Clasificación

Antes de ejecutar cualquier acción sobre las órdenes de venta vencidas, es fundamental completar un análisis exhaustivo que permita clasificar cada registro y determinar el tratamiento más apropiado. Esta fase debe realizarse con sumo cuidado para evitar errores que puedan comprometer la integridad de los datos.

El primer paso consiste en ejecutar un script que extraiga información completa de todas las órdenes de venta con estado vencido o pendiente de entrega con fecha anterior a la fecha actual. Este script debe generar un reporte que incluya el cliente, el valor total, las fechas de creación y entrega, los documentos asociados (notas de entrega, facturas) y cualquier comentario o nota relevante.

```
# Script de análisis para órdenes de venta vencidas
import frappe
from frappe.utils import today, getdate

def analizar_ordenes_vencidas():
    # Obtener fecha actual
    fecha_actual = today()
    
    # Consulta de órdenes vencidas
    ordenes = frappe.get_all(
        "Sales Order",
        filters={
            "delivery_date": ["<", getdate(fecha_actual)],
            "status": ["in", ["To Deliver", "To Deliver and Bill", "Partial"]]
        },
        fields=["name", "customer_name", "grand_total", "delivery_date", 
                "transaction_date", "status", "per_delivered", "per_billed"],
        order_by="grand_total desc"
    )
    
    print(f"Se encontraron {len(ordenes)} órdenes de venta vencidas\n")
    
    reporte = []
    for orden in ordenes:
        # Verificar documentos asociados
        delivery_notes = frappe.get_all(
            "Delivery Note",
            filters={"against_sales_order": orden.name},
            fields=["name", "docstatus"]
        )
        
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={"sales_order": orden.name},
            fields=["name", "docstatus"]
        )
        
        info = {
            "nombre": orden.name,
            "cliente": orden.customer_name,
            "valor": orden.grand_total,
            "fecha_entrega": orden.delivery_date,
            "estado": orden.status,
            "entregado_pct": orden.per_delivered,
            "facturado_pct": orden.per_billed,
            "notas_entrega": len(delivery_notes),
            "facturas": len(sales_invoices)
        }
        reporte.append(info)
        
        print(f"Orden: {info['nombre']}")
        print(f"  Cliente: {info['cliente']}")
        print(f"  Valor: ${info['valor']:,.2f}")
        print(f"  Fecha entrega: {info['fecha_entrega']}")
        print(f"  Estado: {info['estado']}")
        print(f"  Notas de entrega: {info['notas_entrega']}")
        print(f"  Facturas: {info['facturas']}")
        print()
    
    return reporte

# Ejecutar análisis
reporte = analizar_ordenes_vencidas()
```

### 5.2 Fase 2: Ejecución de Acciones Masivas

Una vez completado el análisis y clasificación, la segunda fase consiste en ejecutar las acciones recomendadas para cada categoría de órdenes. Esta fase debe realizarse en subfases para permitir verificación entre cada conjunto de cambios.

**Subfase 2a: Cierre de órdenes sin documentos asociados**

Para las órdenes que no tienen notas de entrega ni facturas asociadas, y que han sido clasificadas como "canceladas verbalmente" o "abandonadas", se recomienda proceder con el cierre:

```
# Script para cerrar órdenes sin documentos asociados
import frappe

def cerrar_ordenes_sin_documentos():
    # Lista de órdenes a cerrar (reemplazar con resultados del análisis)
    ordenes_a_cerrar = [
        "SO-117326-AGROMAYAL BOTÁNICA",
        "SO-117026-BARENTZ Service S.p.A.",
        # Agregar más órdenes según análisis
    ]
    
    cerradas = []
    errores = []
    
    for nombre in ordenes_a_cerrar:
        try:
            so = frappe.get_doc("Sales Order", nombre)
            
            # Verificar que no tenga documentos asociados
            tiene_dn = frappe.db.exists("Delivery Note", {"against_sales_order": nombre})
            tiene_si = frappe.db.exists("Sales Invoice", {"sales_order": nombre})
            
            if tiene_dn or tiene_si:
                print(f"Saltando {nombre}: tiene documentos asociados")
                continue
            
            # Cerrar la orden
            so.status = "Closed"
            so.add_comment("Comment", "Orden cerrada durante limpieza de datos de migración")
            so.save(flags={"ignore_permissions": True})
            frappe.db.commit()
            
            cerradas.append(nombre)
            print(f"✓ Cerrada: {nombre}")
            
        except Exception as e:
            errores.append({"orden": nombre, "error": str(e)})
            print(f"✗ Error en {nombre}: {e}")
    
    print(f"\nResumen: {len(cerradas)} cerradas, {len(errores)} errores")
    return {"cerradas": cerradas, "errores": errores}

resultado = cerrar_ordenes_sin_documentos()
```

**Subfase 2b: Cancelación de órdenes erroneousas**

Para las órdenes que claramente corresponden a errores de migración y no tienen documentos asociados, se puede proceder con la cancelación:

```
# Script para cancelar órdenes con errores de migración
import frappe

def cancelar_ordenes_error():
    # Lista de órdenes a cancelar (verificar primero con análisis)
    ordenes_a_cancelar = [
        # Agregar órdenes identificadas como error de migración
    ]
    
    canceladas = []
    errores = []
    
    for nombre in ordenes_a_cancelar:
        try:
            so = frappe.get_doc("Sales Order", nombre)
            
            # Verificaciones de seguridad
            if so.docstatus != 1:
                print(f"Saltando {nombre}: no está enviada")
                continue
            
            tiene_dn = frappe.db.exists("Delivery Note", {"against_sales_order": nombre, "docstatus": 1})
            tiene_si = frappe.db.exists("Sales Invoice", {"sales_order": nombre, "docstatus": 1})
            
            if tiene_dn or tiene_si:
                print(f"Saltando {nombre}: tiene documentos submitidos")
                continue
            
            # Cancelar
            so.cancel()
            frappe.db.commit()
            
            canceladas.append(nombre)
            print(f"✓ Cancelada: {nombre}")
            
        except Exception as e:
            errores.append({"orden": nombre, "error": str(e)})
            print(f"✗ Error en {nombre}: {e}")
    
    return {"canceladas": canceladas, "errores": errores}
```

### 5.3 Fase 3: Verificación y Documentación

La tercera fase del plan de acción consiste en verificar los resultados de las modificaciones realizadas y documentar los cambios realizados para futura referencia. Esta fase es crítica para mantener la trazabilidad y facilitar auditorías futuras.

```
# Script de verificación post-ejecución
import frappe
from frappe.utils import today

def verificar_estado_final():
    # Órdenes que fueron procesadas
    ordenes_procesadas = [
        "SO-117326-AGROMAYAL BOTÁNICA",
        "SO-117026-BARENTZ Service S.p.A.",
        "SO-116926-LORAND LABORATORIES LLC"
    ]
    
    print("VERIFICACIÓN DE ESTADO FINAL")
    print("=" * 60)
    
    for nombre in ordenes_procesadas:
        try:
            so = frappe.get_doc("Sales Order", nombre)
            print(f"\n{nombre}")
            print(f"  Estado actual: {so.status}")
            print(f"  Fecha última modificación: {so.modified}")
            
            # Obtener comentarios
            comentarios = frappe.get_all(
                "Comment",
                filters={
                    "reference_doctype": "Sales Order",
                    "reference_name": nombre
                },
                fields=["content", "creation"],
                order_by="creation desc"
            )
            
            if comentarios:
                print(f"  Último comentario: {comentarios[0].content}")
                
        except Exception as e:
            print(f"\n{nombre}")
            print(f"  Error al verificar: {e}")

verificar_estado_final()
```

---

## 6. Comandos de Referencia Rápida

### 6.1 Comandos de Consola Bench

A continuación se presenta una colección de comandos útiles para la gestión de órdenes de venta desde la línea de comandos de Bench:

```
# Ver todas las órdenes de venta con estado específico
bench execute frappe.client.get_list --kwargs '{"doctype": "Sales Order", "filters": {"status": ["Like", "%To Deliver%"]}, "fields": ["name", "customer_name", "grand_total", "delivery_date", "status"]}'

# Obtener detalles de una orden específica
bench execute frappe.client.get --kwargs '{"doctype": "Sales Order", "name": "SO-117326-AGROMAYAL BOTÁNICA"}'

# Actualizar estado de una orden (usando set_value)
bench execute frappe.client.set_value --kwargs '{"doctype": "Sales Order", "name": "SO-117326-AGROMAYAL BOTÁNICA", "fieldname": "status", "value": "Closed"}'

# Contar órdenes en cada estado
bench execute frappe.db.sql --kwargs '{"sql": "SELECT status, COUNT(*) as total FROM `tabSales Order` GROUP BY status"}'
```

### 6.2 Consultas SQL Directas

Para análisis más detallados, se pueden ejecutar consultas SQL directamente en la base de datos:

```
-- Órdenes de venta vencidas (sin cumplir completamente)
SELECT 
    name,
    customer_name,
    grand_total,
    delivery_date,
    status,
    per_delivered,
    per_billed
FROM `tabSales Order`
WHERE delivery_date < CURDATE()
    AND status NOT IN ('Closed', 'Cancelled', 'Completed')
ORDER BY grand_total DESC;

-- Órdenes con documentos asociados
SELECT 
    so.name,
    so.customer_name,
    COUNT(DISTINCT dn.name) AS notas_entrega,
    COUNT(DISTINCT si.name) AS facturas
FROM `tabSales Order` so
LEFT JOIN `tabDelivery Note` dn ON dn.against_sales_order = so.name
LEFT JOIN `tabSales Invoice` si ON si.sales_order = so.name
WHERE so.delivery_date < CURDATE()
    AND so.status NOT IN ('Closed', 'Cancelled')
GROUP BY so.name
HAVING notas_entrega > 0 OR facturas > 0;
```

---

## 7. Conclusiones y Recomendaciones Finales

### 7.1 Síntesis del Análisis

El análisis realizado sobre las órdenes de venta vencidas provenientes de la migración de datos en ERPNext revela un escenario que requiere atención cuidadosa pero no representa una situación crítica siempre que se sigan los procedimientos adecuados. Las ocho órdenes identificadas, con un valor total que supera los $11 millones de pesos mexicanos solo en las tres específicamente documentadas, representan compromisos comerciales que necesitan resolverse para mantener la integridad operativa del sistema.

Las opciones disponibles en ERPNext para 处理 estas situaciones (cerrar, detener o cancelar) ofrecen flexibilidad suficiente para abordar cada escenario de manera apropiada, siempre que se realice el análisis previo necesario para determinar la acción correcta para cada registro específico. La recomendación principal es proceder con cautela, priorizando la preservación de datos cuando exista duda y ejecutando cambios de manera gradual para permitir la verificación de resultados.

### 7.2 Pasos Inmediatos Recomendados

Se recomienda al usuario ejecutar las siguientes acciones en orden prioritario:

**Primero**, ejecutar el script de análisis proporcionado en la Fase 1 para obtener una visión completa de todas las órdenes de venta vencidas en el sistema, incluyendo las cinco adicionales que no fueron específicamente documentadas en la solicitud inicial.

**Segundo**, coordinar con el equipo comercial la revisión de las tres órdenes específicamente documentadas, particularmente SO-117326-AGROMAYAL BOTÁNICA dado su alto valor, para confirmar el estado actual de la relación con cada cliente.

**Tercero**, una vez obtenida la validación del equipo comercial, proceder con el cierre o cancelación de las órdenes según la clasificación determinada, ejecutando primero las acciones sobre registros sin documentos asociados.

**Cuarto**, documentar todos los cambios realizados en un formato que facilite futuras auditorías, incluyendo el responsable, la fecha, la justificación y el resultado de cada acción.

### 7.3 Consideraciones de Riesgo

Es importante considerar que la ejecución de acciones sobre datos de migración tiene riesgos inherentes que deben ser mitigados. Los principal es realizar siempre un backup de la base de datos antes de ejecutar modificaciones masivas. Adicionalmente, se recomienda ejecutar los scripts primero en un entorno de pruebas o sandbox antes de implementarlos en producción. Finalmente, cualquier acción que involucre datos financieros debe ser validada por el equipo contable para asegurar el cumplimiento de las políticas de la organización.

---

*Documento preparado para AMB-Wellness - Sistema ERPNext*  
*Fecha de elaboración: Marzo 2026*