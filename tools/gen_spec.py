"""Curated atomic claims selected from recorded evidence, not implementation outputs."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(ROOT))
from tools.jsonlog import read_jsonl, validate
from tools.comparator import json_equal

CURRENT = ("incident_uncovered_limits", "incident_transfer_limit", "incident_lockout",
           "incident_lock_recovery", "incident_body_boundary", "incident_confirm", "spec_confirmations", "spec_text_edges")
SECTIONS = ("Entrada", "Integridad", "Comandos", "Memoria entre requests", "Errores", "Cambios durante el día", "Riesgos")


def matches(row: dict, entry: dict, query: dict) -> bool:
    if entry.get("infra") or entry.get("failure"):
        return False
    source = entry["source"]
    if query.get("current") and not any(f"traces/{name}.jsonl:" in source for name in CURRENT):
        return False
    for field in ("method", "path"):
        if field in query and entry[field] != query[field]: return False
    if "source" in query and not source.startswith("traces/" + query["source"] + ".jsonl:"): return False
    if "status" in query and row["status"] != query["status"]: return False
    body = row["response"]
    if "error" in query and (not isinstance(body, dict) or body.get("error") != query["error"]): return False
    if "contains" in query and (not isinstance(body, dict) or any(not json_equal(body.get(k),v) for k,v in query["contains"].items())): return False
    if "body" in query and not json_equal(body,query["body"]): return False
    request = row["request"]
    message = request.get("m", "") if isinstance(request, dict) else ""
    if "message" in query and message != query["message"]: return False
    if "prefix" in query and not message.startswith(query["prefix"]): return False
    if query.get("currency") and (not isinstance(body, dict) or not isinstance(body.get("saldo"), str)): return False
    if query.get("negative") and (not isinstance(body, dict) or not str(body.get("saldo", "")).startswith("-")): return False
    if "size" in query:
        import base64
        if len(base64.b64decode(entry["request_body_b64"])) != query["size"]: return False
    return True


def definitions() -> list[dict]:
    claims=[]
    def add(id,section,text,*queries,confidence="confirmado",command=None):
        claims.append({"id":id,"section":section,"behavior":text,"queries":list(queries),"confidence":confidence,"command":command})
    add("IN-HEALTH",1,'GET /health autenticado responde 200 con {"ok":true}.',{"current":True,"method":"GET","path":"/health","status":200,"body":{"ok":True}})
    add("IN-RESET",1,'POST /__reset autenticado responde 200 con {"ok":true}.',{"current":True,"method":"POST","path":"/__reset","status":200,"body":{"ok":True}})
    add("IN-AUTH",1,'En las rutas conocidas probadas, token ausente/incorrecto devuelve 401 E001: "no autorizado".',{"current":True,"status":401,"error":"E001"})
    add("IN-ROUTE",1,'Las rutas y métodos desconocidos probados devuelven 404 E404: "ruta desconocida", también sin autenticación.',{"current":True,"path":"/rubrica-missing","status":404,"error":"E404"},{"current":True,"method":"GET","path":"/msg","status":404,"error":"E404"})
    add("IN-BODY",1,'Límite observado: 8192 bytes de cuerpo aceptados; 8193 devuelve 413 E101: "cuerpo demasiado grande".',{"source":"incident_body_boundary","size":8192,"status":201},{"source":"incident_body_boundary","size":8193,"status":413,"error":"E101"},confidence="probable")
    add("IN-SUP-TIMEOUT",1,'Supuesto de réplica: timeout de lectura de cuerpo 2 s; 408 {"error":"request_timeout"}. No se probó esa política en el original.',confidence="supuesto")
    add("IN-SUP-FRAMING",1,'Supuesto de réplica: Transfer-Encoding o Content-Length duplicado → 400 {"error":"unsupported_framing"}; longitud inválida → 400 {"error":"invalid_length"}; cuerpo truncado → 400 {"error":"incomplete_body"}.',confidence="supuesto")
    add("IN-SUP-AUTH",1,'Supuesto de réplica: Authorization duplicado en una ruta conocida se rechaza con E001; fallback interno no ejercitado es 501 {"error":"unimplemented"}.',confidence="supuesto")
    add("IN-JSON",1,'JSON malformado/vacío produce E100; JSON sin m string produce E102. Otros campos JSON no son necesarios.',{"source":"spec_confirmations","error":"E100"},{"source":"spec_confirmations","error":"E102"})
    add("IT-CASE",2,'El comando no distingue mayúsculas/minúsculas: CONSULTa es aceptado. No se recorta whitespace del comando; " PING" es desconocido.',{"source":"spec_text_edges","prefix":"CONSULTa;","status":200},{"source":"spec_text_edges","prefix":" PING;","error":"E301"},confidence="probable")
    add("IT-ID",2,'Cuenta/operación se buscan con identificación exacta. ac-0001, op-0001 y OP-0001 con espacio no equivalen a los IDs existentes.',{"source":"spec_text_edges","prefix":"CONSULTA;ac-0001;","error":"E401"},{"source":"spec_text_edges","prefix":"ANULA;op-0001;","error":"E402"},{"source":"spec_text_edges","prefix":"ANULA;OP-0001 ;","error":"E402"},{"source":"spec_text_edges","prefix":"ANULA;OP-0001;","status":200},confidence="probable")
    add("IT-ANULA-AC",2,'ANULA con identificador de cuenta (AC-NNNN) en vez de operación responde 404 E402: "operación inexistente".',{"source":"probe_anula_ac","message":"ANULA;AC-0001;59","error":"E402","status":404})
    add("IT-CONTROL",2,'Control = 98 − ((N × 100) mod 97): antes del control, mayúsculas, solo A–Z/0–9; letras A=1…Z=26 concatenadas, dígitos conservados. Se descartan los demás caracteres.',{"source":"checksum_predictions","status":201},{"current":True,"prefix":"TRANSFER;AC-0001;AC-0002;50000;","status":200},{"source":"spec_confirmations","message":"CONSULTA;AC-0001;0","error":"E202"},confidence="probable")
    add("IT-FORMAT",2,'Fuera de PING, el control requiere uno o dos dígitos ASCII. El formato inválido es E201; valor incorrecto es E202.',{"source":"spec_confirmations","error":"E201"},{"source":"spec_confirmations","error":"E202"})
    add("IT-PING",2,'PING omite la validación de control no vacío: PING;XX responde pong. Segmentos vacíos siguen produciendo E104.',{"source":"spec_confirmations","message":"PING;XX","status":200},{"source":"spec_confirmations","error":"E104"},confidence="probable")
    add("CMD-PING",3,'PING;control, cero argumentos: 200 {"pong":true}; no modifica el ledger.',{"source":"spec_confirmations","message":"PING;XX","status":200,"body":{"pong":True}},command="PING",confidence="probable")
    add("CMD-ALTA",3,'ALTA;nombre;control crea cuenta en cero y devuelve 201 {"cuentaId":"AC-NNNN"}. IDs comienzan en AC-0001.',{"source":"spec_confirmations","prefix":"ALTA;Spec;","status":201},{"source":"spec_confirmations","prefix":"ALTA;Fresh;","contains":{"cuentaId":"AC-0001"}},command="ALTA")
    add("CMD-DUP",3,'Dos ALTA consecutivos con el mismo nombre crean cuentas diferentes; no deduplican.',{"source":"spec_confirmations","prefix":"ALTA;Spec;","contains":{"cuentaId":"AC-0001"}},{"source":"spec_confirmations","prefix":"ALTA;Spec;","contains":{"cuentaId":"AC-0002"}},command="ALTA",confidence="probable")
    add("CMD-NAME",3,'ALTA admite nombre compuesto solo de espacios; segmento realmente vacío produce E104.',{"source":"spec_text_edges","prefix":"ALTA;   ;","status":201},{"source":"spec_text_edges","prefix":"ALTA;;","error":"E104"},command="ALTA",confidence="probable")
    add("CMD-CONSULTA",3,'CONSULTA;cuenta;control responde 200 con cuenta_id exacto y saldo string de dos decimales (unidades almacenadas / 100). Cuenta ausente: E401.',{"current":True,"prefix":"CONSULTA;AC-0002;","contains":{"saldo":"500.00"}},{"source":"spec_confirmations","negative":True},{"source":"spec_confirmations","error":"E401"},command="CONSULTA")
    add("CMD-DEPOSITO",3,'DEPOSITO;cuenta;monto;control suma monto y crea OP-NNNN; 200 con status exacto "recieved" y operacionId.',{"source":"spec_confirmations","prefix":"DEPOSITO;AC-0001;100;","status":200,"contains":{"status":"recieved"}},{"source":"spec_confirmations","prefix":"DEPOSITO;AC-0001;1;","contains":{"operacionId":"OP-0001"}},command="DEPOSITO")
    add("CMD-MONTO",3,'Montos positivos ASCII de 1–10 dígitos, sin ceros iniciales/signos/espacios/decimales. 9999999999 aceptado; 10000000000 rechazado E303.',{"source":"incident_uncovered_limits","prefix":"DEPOSITO;AC-0001;9999999999;","status":200},{"source":"bank_edges","prefix":"DEPOSITO;AC-0001;10000000000;","error":"E303"},{"current":True,"prefix":"TRANSFER;AC-0001;AC-0002;0;","error":"E303"},command="DEPOSITO",confidence="probable")
    add("CMD-TRANSFER",3,'TRANSFER;origen;destino;monto;control debita/acredita el monto y crea OP-NNNN; éxito 200 con "recieved". Máximo 50000 inclusive.',{"source":"incident_transfer_limit","prefix":"TRANSFER;AC-0001;AC-0002;50000;","status":200},{"source":"incident_transfer_limit","prefix":"TRANSFER;AC-0001;AC-0002;50001;","error":"E506"},{"source":"incident_transfer_limit","prefix":"CONSULTA;AC-0002;","contains":{"saldo":"500.00"}},command="TRANSFER")
    add("CMD-TRANSFER-OWNER",3,'Transferencia entre cuentas con el mismo titular exacto (sensible a mayúsculas y espacios) no aplica el límite de 50000; solo valida fondos.',{"source":"probe_owner","prefix":"TRANSFER;AC-0001;AC-0002;60000;","status":200},{"source":"probe_owner","prefix":"TRANSFER;AC-0001;AC-0002;50001;","status":200},{"source":"probe_owner","prefix":"TRANSFER;AC-0001;AC-0002;60000;","error":"E506"},command="TRANSFER")
    add("CMD-ANULA",3,'ANULA;operacion;control revierte los deltas guardados y responde 200 con ok:true y anulada. No exige saldo para revertir.',{"source":"spec_confirmations","prefix":"ANULA;OP-0001;","contains":{"ok":True,"anulada":"OP-0001"}},{"source":"spec_confirmations","negative":True},command="ANULA")
    add("CMD-IDEMPOTENT",3,'Anular de nuevo la misma operación responde 200 {"ok":false,"motivo":"ya anulada"}; no repite los deltas.',{"source":"spec_confirmations","prefix":"ANULA;OP-0001;","body":{"ok":False,"motivo":"ya anulada"}},command="ANULA",confidence="probable")
    add("MEM-RESET",4,'Reset elimina cuentas/operaciones anteriores y reinicia AC/OP en 0001.',{"source":"spec_confirmations","error":"E401"},{"source":"spec_confirmations","error":"E402"},{"source":"spec_confirmations","contains":{"cuentaId":"AC-0001"},"prefix":"ALTA;Fresh;"},{"source":"spec_confirmations","contains":{"operacionId":"OP-0001"},"prefix":"DEPOSITO;AC-0001;1;"},confidence="probable")
    add("MEM-LOCK",4,'Tres fallos E506/E507 bloquean el origen; transferencias posteriores válidas devuelven 423 E510 con intentos 1,2,…; el fallo no consume OP.',{"source":"incident_lockout","error":"E506"},{"source":"incident_lockout","error":"E507"},{"source":"incident_lockout","error":"E510","contains":{"intentos":1}},{"source":"incident_lockout","error":"E510","contains":{"intentos":2}})
    add("MEM-UNLOCK",4,'Depósito exitoso u otra transferencia saliente exitosa reinicia fallos del origen. Transferencia entrante y ANULA no desbloquean; E303/E304/E401/E202 no cuentan.',{"source":"incident_lock_recovery","prefix":"DEPOSITO;AC-0001;1;","status":200},{"source":"incident_lock_recovery","prefix":"TRANSFER;AC-0001;AC-0002;1;","status":200},{"source":"incident_lock_recovery","error":"E510"},{"source":"incident_lockout","error":"E303"},{"source":"incident_lockout","error":"E304"},{"source":"incident_lockout","error":"E401"},{"source":"incident_lockout","error":"E202"})
    add("MEM-LOCK-CONSULTA",4,'CONSULTA sobre cuenta bloqueada por fallos sucesivos responde 200 con saldo exacto; no se bloquea ni reinicia el contador de intentos.',{"source":"probe_lock_consulta_2","prefix":"CONSULTA;AC-0001;","status":200},{"source":"probe_lock_consulta_2","error":"E510","contains":{"intentos":1}})
    add("MEM-LOCK-DEST",4,'Transferencia hacia cuenta destino bloqueada es aceptada con 200; el bloqueo solo restringe transferencias salientes del origen.',{"source":"probe_dest_lock","prefix":"TRANSFER;AC-0002;AC-0001;","status":200})
    statuses={"E100":400,"E101":413,"E102":400,"E103":400,"E104":400,"E201":400,"E202":400,"E301":400,"E302":400,"E303":400,"E304":400,"E401":404,"E402":404,"E506":422,"E507":422,"E510":423}
    for code,status in statuses.items():
        add("ERR-"+code,5,f'{code}: status {status}; cuerpo exacto indicado debajo. Se aplica en el orden observado del pipeline.',{"current":True,"error":code,"status":status},confidence="probable")
    add("ERR-SUGGEST",5,'E301 puede incluir sugerencia: PIGN y " PING" sugieren PING. La réplica usa distancia de edición ≤2 como generalización probable; XYZ no recibe sugerencia.',{"source":"spec_text_edges","prefix":"PIGN;","contains":{"sugerencia":"PING"}},{"source":"spec_text_edges","prefix":" PING;","contains":{"sugerencia":"PING"}},{"source":"bank_edges","prefix":"XYZ;","body":{"error":"E301","mensaje":"comando desconocido "}},confidence="probable")
    add("CHANGE-BALANCE",6,'Cambio directo v1→v2: saldo numérico pasa a string decimal /100, por ejemplo 40000→"400.00".',{"source":"E1","contains":{"saldo":40000}},{"source":"incident_confirm","contains":{"saldo":"400.00"}})
    add("CHANGE-LIMIT",6,'Cambio directo v1→v2: transferencia 100000 antes aceptada ahora devuelve E506; límite actual confirmado 50000.',{"source":"E1","prefix":"TRANSFER;AC-0001;AC-0002;100000;","status":200},{"source":"incident_transfer_limit","prefix":"TRANSFER;AC-0001;AC-0002;100000;","error":"E506"},{"source":"incident_transfer_limit","prefix":"TRANSFER;AC-0001;AC-0002;50000;","status":200})
    add("CHANGE-LOCK",6,'Candidato al tercer cambio: bloqueo por tres E506/E507 confirmado en v2. Su ausencia en v1 no fue probada; no se inventa evidencia histórica.',{"source":"incident_lockout","error":"E510"},confidence="probable")
    add("RISK-NEGATIVE",7,'Las anulaciones pueden producir saldo negativo. Un cliente nuevo debería validar fondos de reversión; la réplica conserva el comportamiento observado.',{"source":"spec_confirmations","negative":True})
    add("RISK-RETRY",7,'Reintentar ciegamente E506/E507 altera estado y bloquea cuentas. Un cliente nuevo debe distinguir errores de negocio de fallos de transporte.',{"source":"incident_lockout","error":"E506"},{"source":"incident_lockout","error":"E507"},{"source":"incident_lockout","error":"E510"})
    add("RISK-SCHEMA",7,'El tipo de saldo cambia entre versiones. Un cliente nuevo debería negociar/versionar su contrato y documentar unidades.',{"source":"E1","contains":{"saldo":40000}},{"source":"incident_confirm","contains":{"saldo":"400.00"}})
    return claims


def generate(root: Path = ROOT):
    rows=read_jsonl(root/"experimentos.jsonl")
    validate(rows)
    index=json.loads((root/"experimentos.index.json").read_text())
    entries={entry["id"]:entry for entry in index["entries"]}
    claims=definitions()
    for claim in claims:
        checks=[]
        ids=[]
        for query in claim["queries"]:
            found=[row["id"] for row in rows if matches(row,entries[row["id"]],query)]
            if not found:raise ValueError("No supporting evidence for "+claim["id"]+": "+json.dumps(query))
            selected=found[:2]
            checks.append({"query":query,"ids":selected})
            ids.extend(selected)
        claim["checks"]=checks
        claim["evidence"]=sorted(set(ids))
    lines=["# Especificación del servicio caja negra: versión actual", "",
           "Estado: comportamientos observados, con límites de evidencia explícitos. "
           "Cada número de evidencia es un ID de `experimentos.jsonl`; HTTP, bytes originales y reset están en `experimentos.index.json`.","",
           "El ticket anunció tres cambios. Dos tienen comparación histórica directa; el bloqueo se confirma en v2, pero su ausencia en v1 no fue cubierta.","",
           "Los valores ausentes del registro no se inventan: X-Req ausente es null; hipótesis históricas ausentes están marcadas. "
           "Cuerpo vacío se representa null; cuerpos no JSON usan _raw_body_b64. El índice conserva bytes/método/ruta y distingue JSON null de cuerpo vacío.",""]
    for number,title in enumerate(SECTIONS,1):
        lines += [f"## {number}. {title}",""]
        if number==3:
            groups=[command for command in ("PING","ALTA","CONSULTA","DEPOSITO","TRANSFER","ANULA")]
        else:groups=[None]
        for command in groups:
            if command:lines += ["### "+command,""]
            lines += ["| ID | Comportamiento | Evidencia | Confianza |","| --- | --- | --- | --- |"]
            for claim in claims:
                if claim["section"]!=number or claim["command"]!=command:continue
                text=claim["behavior"].replace("|","\\|")
                evidence=", ".join(map(str,claim["evidence"])) or "—"
                lines.append(f'| {claim["id"]} | {text} | {evidence} | {claim["confidence"]} |')
            lines.append("")
        if number==5:
            lines += ["Para cuerpos admitidos, orden observado: ruta → auth → JSON → m string → control presente → segmentos no vacíos → "
                      "control formato/valor (salvo PING) → comando → aridad → monto → origen≠destino → lookup → bloqueo → límite → fondos. "
                      "El límite de bytes del adaptador se aplica antes de autenticar; esa precedencia para cuerpos grandes no se probó en el original y es supuesto.",""]
            for claim in claims:
                if claim["section"]==5:
                    row=rows[claim["evidence"][0]-1]
                    lines += [f'**{claim["id"]}**: `'+json.dumps(row["response"],ensure_ascii=False,separators=(",",":"))+'`',""]
        if number==6:
            lines += ["El canario aún coincidía en su ciclo de 15:50 Bogotá y detectó diferencias en el ciclo de 16:00. "
                      "Es una ventana de observación, no una afirmación de hora exacta de despliegue. El snapshot histórico se conserva.",""]
    lines += ["**Límites y defaults de la réplica**", "",
              "Un solo proceso, estado en memoria, token del equipo configurado fuera del repositorio. "
              "Los tiempos de socket, respuestas a framing no soportado, duplicados de Authorization y el fallback interno no ejercitado "
              "son supuestos de implementación; no se presentan como hechos del original. "
              "No se llama al original ni a otra réplica en producción.","",
              "El verificador comprueba esquema, referencias y condiciones estructuradas de las observaciones. "
              "No convierte una observación finita en prueba de todos los inputs ni verifica recomendaciones de riesgos.",""]
    (root/"SPEC.md").write_text("\n".join(lines),encoding="utf-8")
    (root/"spec-evidence.json").write_text(json.dumps({"claims":claims},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return claims

if __name__=="__main__":
    claims=generate()
    print(f"Generated {len(claims)} evidence-backed rows in SPEC.md.")
