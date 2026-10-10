# Especificación del servicio caja negra: versión actual

Estado: comportamientos observados, con límites de evidencia explícitos. Cada número de evidencia es un ID de `experimentos.jsonl`; HTTP, bytes originales y reset están en `experimentos.index.json`.

El ticket anunció tres cambios. Dos tienen comparación histórica directa; el bloqueo se confirma en v2, pero su ausencia en v1 no fue cubierta.

Los valores ausentes del registro no se inventan: X-Req ausente es null; hipótesis históricas ausentes están marcadas. Cuerpo vacío se representa null; cuerpos no JSON usan _raw_body_b64. El índice conserva bytes/método/ruta y distingue JSON null de cuerpo vacío.

## 1. Entrada

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| IN-HEALTH | GET /health autenticado responde 200 con {"ok":true}. | 1156 | confirmado |
| IN-RESET | POST /__reset autenticado responde 200 con {"ok":true}. | 993, 1016 | confirmado |
| IN-AUTH | En las rutas conocidas probadas, token ausente/incorrecto devuelve 401 E001: "no autorizado". | 1180, 1181 | confirmado |
| IN-ROUTE | Las rutas y métodos desconocidos probados devuelven 404 E404: "ruta desconocida", también sin autenticación. | 1177, 1179 | confirmado |
| IN-BODY | Límite observado: 8192 bytes de cuerpo aceptados; 8193 devuelve 413 E101: "cuerpo demasiado grande". | 1153, 1154 | probable |
| IN-SUP-TIMEOUT | Supuesto de réplica: timeout de lectura de cuerpo 2 s; 408 {"error":"request_timeout"}. No se probó esa política en el original. | — | supuesto |
| IN-SUP-FRAMING | Supuesto de réplica: Transfer-Encoding o Content-Length duplicado → 400 {"error":"unsupported_framing"}; longitud inválida → 400 {"error":"invalid_length"}; cuerpo truncado → 400 {"error":"incomplete_body"}. | — | supuesto |
| IN-SUP-AUTH | Supuesto de réplica: Authorization duplicado en una ruta conocida se rechaza con E001; fallback interno no ejercitado es 501 {"error":"unimplemented"}. | — | supuesto |
| IN-JSON | JSON malformado/vacío produce E100; JSON sin m string produce E102. Otros campos JSON no son necesarios. | 1210, 1211, 1212, 1213 | confirmado |

## 2. Integridad

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| IT-CASE | El comando no distingue mayúsculas/minúsculas: CONSULTa es aceptado. No se recorta whitespace del comando; " PING" es desconocido. | 1267, 1271 | probable |
| IT-ID | Cuenta/operación se buscan con identificación exacta. ac-0001, op-0001 y OP-0001 con espacio no equivalen a los IDs existentes. | 1268, 1269, 1270, 1273 | probable |
| IT-ANULA-AC | ANULA con identificador de cuenta (AC-NNNN) en vez de operación responde 404 E402: "operación inexistente". | 1445 | confirmado |
| IT-CONTROL | Control = 98 − ((N × 100) mod 97): antes del control, mayúsculas, solo A–Z/0–9; letras A=1…Z=26 concatenadas, dígitos conservados. Se descartan los demás caracteres. | 774, 775, 1026, 1228 | probable |
| IT-FORMAT | Fuera de PING, el control requiere uno o dos dígitos ASCII. El formato inválido es E201; valor incorrecto es E202. | 1227, 1228 | confirmado |
| IT-PING | PING omite la validación de control no vacío: PING;XX responde pong. Segmentos vacíos siguen produciendo E104. | 1215, 1216 | probable |

## 3. Comandos

### PING

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-PING | PING;control, cero argumentos: 200 {"pong":true}; no modifica el ledger. | 1216 | probable |

### ALTA

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-ALTA | ALTA;nombre;control crea cuenta en cero y devuelve 201 {"cuentaId":"AC-NNNN"}. IDs comienzan en AC-0001. | 1217, 1218, 1234 | confirmado |
| CMD-DUP | Dos ALTA consecutivos con el mismo nombre crean cuentas diferentes; no deduplican. | 1217, 1218 | probable |
| CMD-NAME | ALTA admite nombre compuesto solo de espacios; segmento realmente vacío produce E104. | 1265, 1274 | probable |

### CONSULTA

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-CONSULTA | CONSULTA;cuenta;control responde 200 con cuenta_id exacto y saldo string de dos decimales (unidades almacenadas / 100). Cuenta ausente: E401. | 1027, 1223, 1226, 1232 | confirmado |

### DEPOSITO

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-DEPOSITO | DEPOSITO;cuenta;monto;control suma monto y crea OP-NNNN; 200 con status exacto "recieved" y operacionId. | 1219, 1235 | confirmado |
| CMD-MONTO | Montos positivos ASCII de 1–10 dígitos, sin ceros iniciales/signos/espacios/decimales. 9999999999 aceptado; 10000000000 rechazado E303. | 892, 1001, 1075, 1076 | probable |

### TRANSFER

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-TRANSFER | TRANSFER;origen;destino;monto;control debita/acredita el monto y crea OP-NNNN; éxito 200 con "recieved". Máximo 50000 inclusive. | 1026, 1027, 1032 | confirmado |
| CMD-TRANSFER-OWNER | Transferencia entre cuentas con el mismo titular exacto (sensible a mayúsculas y espacios) no aplica el límite de 50000; solo valida fondos. | 2542, 2547, 2557, 2562 | confirmado |

### ANULA

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CMD-ANULA | ANULA;operacion;control revierte los deltas guardados y responde 200 con ok:true y anulada. No exige saldo para revertir. | 1222, 1223, 1226 | confirmado |
| CMD-IDEMPOTENT | Anular de nuevo la misma operación responde 200 {"ok":false,"motivo":"ya anulada"}; no repite los deltas. | 1224 | probable |

## 4. Memoria entre requests

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| MEM-RESET | Reset elimina cuentas/operaciones anteriores y reinicia AC/OP en 0001. | 1232, 1233, 1234, 1235 | probable |
| MEM-LOCK | Tres fallos E506/E507 bloquean el origen; transferencias posteriores válidas devuelven 423 E510 con intentos 1,2,…; el fallo no consume OP. | 1056, 1057, 1059, 1060, 1064, 1065, 1067, 1068 | confirmado |
| MEM-UNLOCK | Depósito exitoso u otra transferencia saliente exitosa reinicia fallos del origen. Transferencia entrante y ANULA no desbloquean; E303/E304/E401/E202 no cuentan. | 1075, 1076, 1084, 1085, 1093, 1094, 1102, 1103, 1113, 1115, 1124, 1134, 1148 | confirmado |
| MEM-LOCK-CONSULTA | CONSULTA sobre cuenta bloqueada por fallos sucesivos responde 200 con saldo exacto; no se bloquea ni reinicia el contador de intentos. | 1458, 1459 | confirmado |
| MEM-LOCK-DEST | Transferencia hacia cuenta destino bloqueada es aceptada con 200; el bloqueo solo restringe transferencias salientes del origen. | 1467 | confirmado |

## 5. Errores

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| ERR-E100 | E100: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1210, 1211 | probable |
| ERR-E101 | E101: status 413; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 996, 997 | probable |
| ERR-E102 | E102: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1212, 1213 | probable |
| ERR-E103 | E103: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1214 | probable |
| ERR-E104 | E104: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1215, 1274 | probable |
| ERR-E201 | E201: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1173, 1227 | probable |
| ERR-E202 | E202: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1102, 1103 | probable |
| ERR-E301 | E301: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1168, 1229 | probable |
| ERR-E302 | E302: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1176, 1230 | probable |
| ERR-E303 | E303: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1075, 1076 | probable |
| ERR-E304 | E304: status 400; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1084, 1085 | probable |
| ERR-E401 | E401: status 404; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1093, 1094 | probable |
| ERR-E402 | E402: status 404; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1169, 1170 | probable |
| ERR-E506 | E506: status 422; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1002, 1003 | probable |
| ERR-E507 | E507: status 422; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1064, 1065 | probable |
| ERR-E510 | E510: status 423; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline. | 1005, 1006 | probable |
| ERR-SUGGEST | E301 puede incluir sugerencia: PIGN y " PING" sugieren PING. La réplica usa distancia de edición ≤2 como generalización probable; XYZ no recibe sugerencia. | 913, 1271, 1272 | probable |

Para cuerpos admitidos, orden observado: ruta → auth → JSON → m string → control presente → segmentos no vacíos → control formato/valor (salvo PING) → comando → aridad → monto → origen≠destino → lookup → bloqueo → límite → fondos. El límite de bytes del adaptador se aplica antes de autenticar; esa precedencia para cuerpos grandes no se probó en el original y es supuesto.

**ERR-E100**: `{"error":"E100","mensaje":"json inválido"}`

**ERR-E101**: `{"error":"E101","mensaje":"cuerpo demasiado grande"}`

**ERR-E102**: `{"error":"E102","mensaje":"falta m"}`

**ERR-E103**: `{"error":"E103","mensaje":"falta control"}`

**ERR-E104**: `{"error":"E104","mensaje":"segmento vacío"}`

**ERR-E201**: `{"error":"E201","mensaje":"control mal formado"}`

**ERR-E202**: `{"error":"E202","mensaje":"control inválido"}`

**ERR-E301**: `{"error":"E301","mensaje":"comando desconocido "}`

**ERR-E302**: `{"error":"E302","mensaje":"aridad inválida"}`

**ERR-E303**: `{"error":"E303","mensaje":"monto inválido"}`

**ERR-E304**: `{"error":"E304","mensaje":"origen y destino iguales"}`

**ERR-E401**: `{"error":"E401","mensaje":"cuenta inexistente"}`

**ERR-E402**: `{"error":"E402","mensaje":"operación inexistente"}`

**ERR-E506**: `{"error":"E506","mensaje":"límite excedido"}`

**ERR-E507**: `{"error":"E507","mensaje":"saldo insuficiente"}`

**ERR-E510**: `{"error":"E510","mensaje":"cuenta bloqueada","intentos":1}`

**ERR-SUGGEST**: `{"error":"E301","mensaje":"comando desconocido "}`

## 6. Cambios durante el día

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| CHANGE-BALANCE | Cambio directo v1→v2: saldo numérico pasa a string decimal /100, por ejemplo 40000→"400.00". | 11, 1164 | confirmado |
| CHANGE-LIMIT | Cambio directo v1→v2: transferencia 100000 antes aceptada ahora devuelve E506; límite actual confirmado 50000. | 13, 1026, 1050 | confirmado |
| CHANGE-LOCK | Candidato al tercer cambio: bloqueo por tres E506/E507 confirmado en v2. Su ausencia en v1 no fue probada; no se inventa evidencia histórica. | 1059, 1060 | probable |

El canario aún coincidía en su ciclo de 15:50 Bogotá y detectó diferencias en el ciclo de 16:00. Es una ventana de observación, no una afirmación de hora exacta de despliegue. El snapshot histórico se conserva.

## 7. Riesgos

| ID | Comportamiento | Evidencia | Confianza |
| --- | --- | --- | --- |
| RISK-NEGATIVE | Las anulaciones pueden producir saldo negativo. Un cliente nuevo debería validar fondos de reversión; la réplica conserva el comportamiento observado. | 1223, 1226 | confirmado |
| RISK-RETRY | Reintentar ciegamente E506/E507 altera estado y bloquea cuentas. Un cliente nuevo debe distinguir errores de negocio de fallos de transporte. | 1056, 1057, 1059, 1060, 1064, 1065 | confirmado |
| RISK-SCHEMA | El tipo de saldo cambia entre versiones. Un cliente nuevo debería negociar/versionar su contrato y documentar unidades. | 11, 1164 | confirmado |

**Límites y defaults de la réplica**

Un solo proceso, estado en memoria, token del equipo configurado fuera del repositorio. Los tiempos de socket, respuestas a framing no soportado, duplicados de Authorization y el fallback interno no ejercitado son supuestos de implementación; no se presentan como hechos del original. No se llama al original ni a otra réplica en producción.

El verificador comprueba esquema, referencias y condiciones estructuradas de las observaciones. No convierte una observación finita en prueba de todos los inputs ni verifica recomendaciones de riesgos.
