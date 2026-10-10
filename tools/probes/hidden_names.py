"""Look for further hidden commands WITHOUT executing any: send NAME+'X' (a non-command, so E301) and read
the `sugerencia` field. If NAME exists the original suggests it. Replica prediction: no suggestion."""
import json, sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.harness import Harness
from tools.hb import Request, auth
NAMES = ("STOP SHUTDOWN KILL EXIT QUIT RESET RESTART REBOOT STATUS STATE ESTADO VERSION VERSIONS HELP AYUDA ECHO DEBUG DUMP "
         "LOG LOGS CONFIG SALDO SALDOS RETIRO RETIRA RETIRAR CIERRE CIERRA BLOQUEA DESBLOQUEA BLOQUEO HISTORIAL MOVIMIENTOS "
         "LISTA LISTAR BAJA BORRA BORRAR DELETE DROP PURGE WIPE CLEAR TRUNCATE FLUSH SYNC BACKUP RESTORE ADMIN ROOT SUDO "
         "REVERSA REVIERTE CANCELA CONFIRMA CONFIRM YES SI OK ACK NOP NOOP TIME FECHA HORA UPTIME METRICS STATS COUNT").split()
h = Harness("probe_hidden_names", "probe_hidden", 200)
tok = h.target.token
found = {}
with h.sequence():
    h.probe(Request("POST", "/__reset", auth(tok)), "hidden-names: reset", '200 {"ok":true}')
    for name in NAMES:
        text = f"{name}X;X"
        body = json.dumps({"m": f"{text};{control(text)}"}).encode()
        r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body),
                    f"does a command {name} exist? send {name}X (not a command)", "400 E301 with no suggestion")
        j = json.loads(r.body)
        if j.get("error") != "E301" or j.get("sugerencia"):
            found[name] = (r.status, j)
print("non-default answers:", json.dumps(found, ensure_ascii=False, indent=1))
