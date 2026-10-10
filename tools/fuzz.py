"""State-aware sequence generator for the differential runner (tools/difftest.py).

The generator simulates the replica while it builds a sequence, so it can aim at interesting
values: balance +-1, the transfer ceiling, the lock threshold, repeated cancels, locked accounts.
It knows the message grammar, so it complements (and does not replace) tools/heldout.py, which is
grammar-agnostic and only measures.

  python3 tools/fuzz.py --seed 11 --count 60 --dry
  python3 tools/fuzz.py --seed 11 --count 60 --max-calls 700
"""
from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(ROOT))

from rubrica.rules.current import initial_state
from rubrica.rules.v2.checksum import control
from tools.difftest import Seq, msg, predict, run, summarize, write_report

NAMES = ("Lucia", "Mateo", "A", "Ana María", "José", "x y", "名前", "O'Brien", "Zoë", "   ", "N" * 40,
         "lucia", "LUCIA", "Lucia ", " Lucia", "AC-0001", "OP-0001", "123", "0", "é", "e\u0301", "😊", "İ", "ß", "SS",
         "a" * 200, "PING", "ALTA", "null", "true", "{}", "\\", '"', "<b>")
FAULTS = ("bad_control", "bad_format", "arity_plus", "arity_minus", "unknown_command", "lower_command",
          "missing_account", "missing_op", "zero_amount", "big_amount", "neg_amount", "decimal_amount",
          "same_account", "empty_arg", "padded_amount", "ping")


def c(prefix: str) -> str:
    return f"{prefix};{control(prefix)}"


class Builder:
    def __init__(self, rng: random.Random):
        self.rng, self.state, self.steps = rng, initial_state(), []

    def add(self, text: str, note: str) -> None:
        step = msg(text, note=note)
        self.state, *_ = predict(self.state, step)
        self.steps.append(step)

    def accounts(self) -> list[str]:
        return [key for key, _, _ in self.state.accounts]

    def ops(self) -> list[str]:
        return [op.id for op in self.state.operations]

    def pick_account(self) -> str:
        return self.rng.choice(self.accounts()) if self.accounts() else "AC-0001"

    def amount_for(self, source: str) -> int:
        balance = self.state.balance(source) or 0
        choices = [1, 2, 100, 49999, 50000, 50001, 10, 777, 1000, 99, 101, 999999, 9999999999]
        if balance > 0:
            choices += [balance, balance + 1, max(1, balance - 1), max(1, balance // 2)] * 3
        return self.rng.choice(choices)

    # --- actions -------------------------------------------------------------------------------
    def alta(self):
        used = [name for _, name, _ in self.state.accounts]
        name = self.rng.choice(used) if used and self.rng.random() < 0.45 else self.rng.choice(NAMES)
        self.add(c(f"ALTA;{name}"), "open an account")

    def deposit(self):
        self.add(c(f"DEPOSITO;{self.pick_account()};{self.rng.choice((1, 100, 1000, 25000, 50000, 50001, 120000, 99999, 100001, 9999999999, 5000000000, 4294967296, 2147483648))}"),
                 "deposit")

    def transfer(self):
        accounts = self.accounts()
        if len(accounts) < 2:
            return self.alta()
        src, dst = self.rng.sample(accounts, 2)
        self.add(c(f"TRANSFER;{src};{dst};{self.amount_for(src)}"), "transfer (value aimed at a boundary)")

    def burn(self):
        """Repeat one failing transfer 1-4 times: aims at the lockout counter."""
        accounts = self.accounts()
        if len(accounts) < 2:
            return self.alta()
        src, dst = self.rng.sample(accounts, 2)
        balance = self.state.balance(src) or 0
        amount = self.rng.choice((50001, 60000, balance + 1 if balance < 50000 else 50001))
        for _ in range(self.rng.randint(1, 4)):
            self.add(c(f"TRANSFER;{src};{dst};{amount}"), "repeat a failing transfer (lockout counter)")

    def drain(self):
        """Deposit, spend it, then cancel the deposit: aims at negative balances and currency format."""
        key = self.pick_account()
        amount = self.rng.choice((100, 1000, 12345))
        self.add(c(f"DEPOSITO;{key};{amount}"), "deposit that will be cancelled after spending")
        accounts = [a for a in self.accounts() if a != key]
        if accounts:
            self.add(c(f"TRANSFER;{key};{accounts[0]};{amount}"), "spend the deposit")
        ops = self.ops()
        dep = next((op.id for op in reversed(self.state.operations) if op.kind == "deposit" and op.destination is None and not op.cancelled), None)
        if dep:
            self.add(c(f"ANULA;{dep}"), "cancel the spent deposit (negative balance?)")
        self.add(c(f"CONSULTA;{key}"), "read the balance after cancel")

    def lock_two(self):
        """Lock two different sources, then try each."""
        accounts = self.accounts()
        if len(accounts) < 3:
            return self.alta()
        a, b, d = accounts[0], accounts[1], accounts[2]
        for src in (a, b):
            for _ in range(3):
                self.add(c(f"TRANSFER;{src};{d};60000"), "fail transfer to lock a source")
        self.add(c(f"TRANSFER;{a};{b};1"), "locked source A")
        self.add(c(f"TRANSFER;{b};{a};1"), "locked source B")
        self.add(c(f"TRANSFER;{d};{a};1"), "healthy source into locked destination")

    def case_command(self):
        cmd = self.rng.choice(("consulta", "Consulta", "deposito", "Transfer", "anula", "AnUlA", "alta", "ping"))
        key = self.pick_account()
        text = {"consulta": f"{cmd};{key}", "Consulta": f"{cmd};{key}", "deposito": f"{cmd};{key};10",
                "Transfer": f"{cmd};{key};{key};1", "anula": f"{cmd};OP-0001", "AnUlA": f"{cmd};OP-0001",
                "alta": f"{cmd};Zed", "ping": "ping"}[cmd]
        self.add("ping;64" if cmd == "ping" else c(text), f"mixed-case command {cmd}")

    def consulta(self):
        self.add(c(f"CONSULTA;{self.pick_account()}"), "query balance")

    def anula(self):
        ops = self.ops()
        key = self.rng.choice(ops) if ops else "OP-0001"
        self.add(c(f"ANULA;{key}"), "cancel an operation")
        if ops and self.rng.random() < 0.3:
            self.add(c(f"ANULA;{key}"), "cancel the same operation again")

    def fault(self):
        kind = self.rng.choice(FAULTS)
        acct, other = self.pick_account(), self.rng.choice(self.accounts() or ["AC-0001"])
        op = self.rng.choice(self.ops() or ["OP-0001"])
        text = {
            "bad_control": f"CONSULTA;{acct};{(control('CONSULTA;' + acct) + 1) % 100}",
            "bad_format": f"CONSULTA;{acct};{self.rng.choice(('5X', '', '007', ' 5', '-1', '100', 'AB'))}",
            "arity_plus": c(f"CONSULTA;{acct};{acct}"),
            "arity_minus": c(f"TRANSFER;{acct};{other}"),
            "unknown_command": c(f"{self.rng.choice(('SALDOS', 'RETIRO', 'DEPOSITOS', 'TRANSFERENCIA', 'ANULAR', 'X'))};{acct}"),
            "lower_command": c(f"{self.rng.choice(('consulta', 'Consulta', 'cOnSuLtA'))};{acct}"),
            "missing_account": c(f"CONSULTA;AC-{self.rng.choice(('0099', '9999', '0000', '1'))}"),
            "missing_op": c(f"ANULA;OP-{self.rng.choice(('0099', '9999', '0000'))}"),
            "zero_amount": c(f"DEPOSITO;{acct};0"),
            "big_amount": c(f"DEPOSITO;{acct};{self.rng.choice(('10000000000', '99999999999', '9' * 12))}"),
            "neg_amount": c(f"TRANSFER;{acct};{other};-5"),
            "decimal_amount": c(f"DEPOSITO;{acct};{self.rng.choice(('1.5', '1,5', '1e3', '0x10', '+5'))}"),
            "same_account": c(f"TRANSFER;{acct};{acct};{self.rng.choice((0, 1, 50001))}"),
            "empty_arg": f"DEPOSITO;;100;{control('DEPOSITO;;100')}",
            "padded_amount": c(f"DEPOSITO;{acct};{self.rng.choice(('007', '00', ' 5', '5 '))}"),
            "ping": "PING;64",
        }[kind]
        if kind == "unknown_command" and op:
            pass
        self.add(text, f"fault: {kind}")


def one(rng: random.Random, index: int) -> Seq:
    b = Builder(rng)
    for _ in range(rng.randint(2, 3)):
        b.alta()
    for key in b.accounts():  # fund accounts so transfers, cancels and lock recovery are reachable
        if rng.random() < 0.8:
            b.add(c(f"DEPOSITO;{key};{rng.choice((500, 1000, 20000, 50000, 80000))}"), "fund an account")
    length = rng.randint(9, 12)
    weights = (("deposit", 2), ("transfer", 6), ("burn", 3), ("consulta", 3), ("anula", 4), ("fault", 3), ("alta", 1),
               ("drain", 2), ("lock_two", 1), ("case_command", 1))
    names, w = zip(*weights)
    while len(b.steps) < length:
        getattr(b, rng.choices(names, w)[0])()
    return Seq(f"F{index:03d}", tuple(b.steps[:12]), "state-aware fuzz")


def build(seed: int, count: int) -> list[Seq]:
    rng = random.Random(seed)
    return [one(rng, i) for i in range(count)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--max-calls", type=int, default=700)
    parser.add_argument("--budget", type=int, default=800)
    args = parser.parse_args()
    seqs = build(args.seed, args.count)
    if args.dry:
        print(f"{len(seqs)} sequences, {sum(len(s.steps) + 1 for s in seqs)} live calls")
        for step in seqs[0].steps:
            print("  ", step.body.decode(), "|", step.note)
        return 0
    from tools.harness import Harness
    harness = Harness(f"fuzz_seed{args.seed}", f"fuzz{args.seed}", args.budget)
    result = run(harness, seqs, label=f"fuzz-{args.seed}", max_calls=args.max_calls)
    print(summarize(result))
    print("report:", write_report(f"fuzz-{args.seed}", result))
    for d in result.divergences:
        print(f" DIVERGENCE {d['sequence']} step {d['step']} rule={d['rule']}\n    request:   {d['request']['body']}"
              f"\n    predicted: {d['predicted'][:110]}\n    original:  {d['original'][:110]}")
    return 1 if result.divergences else 0


if __name__ == "__main__":
    raise SystemExit(main())
