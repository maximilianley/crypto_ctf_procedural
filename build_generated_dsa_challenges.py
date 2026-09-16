from __future__ import annotations

import hashlib
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from pprint import pformat

from Crypto.Util.number import bytes_to_long, inverse, isPrime, long_to_bytes

from generator import generate_formula, format_affine

OUTPUT_DIR = Path(__file__).with_name("generated_challenges")
CHALLENGE_COUNT = 3
SEED_START = 789
SEED_STRIDE = 1000003

GENERATOR_OPTIONS = {
    "alias_count":                      2,
    "extra_terms":                      0,
    "complexity":                       "low",
    "direct_alias_product_rate":        0.0,
    "coefficient_rate":                 0.1,
    "raw_linear_terms_min":             1,
    "raw_linear_terms_max":             1,
    "other_constants_min":              1,
    "other_constants_max":              1,
    "constant_min_appearances":         1,
    "constant_min_product_appearances": 1,
    "inverse_rate":                     0.3,
    "inverse_min_appearances":          1,
    "inverse_min_product_appearances":  0,
    "mult_inverse":                     True,
}


def formal_to_data(formal: dict[tuple[str, ...], int]) -> list[dict[str, object]]:
    return [
        {"monomial": list(monomial), "coefficient": coefficient}
        for monomial, coefficient in sorted(formal.items())
    ]


def subtract_formal(
    left: dict[tuple[str, ...], int],
    right: dict[tuple[str, ...], int],
) -> dict[tuple[str, ...], int]:
    result = dict(left)
    for monomial, coefficient in right.items():
        result[monomial] = result.get(monomial, 0) - coefficient
        if result[monomial] == 0:
            del result[monomial]
    return result


def quadratic_difference(
    lhs: tuple[dict[tuple[str, ...], int], dict[tuple[str, ...], int], dict[tuple[str, ...], int]],
    rhs: tuple[dict[tuple[str, ...], int], dict[tuple[str, ...], int], dict[tuple[str, ...], int]],
) -> tuple[dict[tuple[str, ...], int], dict[tuple[str, ...], int], dict[tuple[str, ...], int]]:
    return (
        subtract_formal(lhs[0], rhs[0]),
        subtract_formal(lhs[1], rhs[1]),
        subtract_formal(lhs[2], rhs[2]),
    )


def indent_block(lines: list[str], prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" if line else "" for line in lines)


def server_expr_from_rhs(rhs_text: str, state_aliases: list[str], constants: list[str], q_symbol: str) -> str:
    expr = transform_visible_rhs_to_python(rhs_text, "__QMOD__")
    for name in sorted(set(constants + state_aliases), key=len, reverse=True):
        expr = re.sub(rf"\b{name}\b", f"self.{name}", expr)
    expr = expr.replace("__QMOD__", q_symbol)
    return expr


def eval_formal_data(terms: list[dict[str, object]], env: dict[str, int], q: int) -> int:
    total = 0
    for term in terms:
        value = int(term["coefficient"]) % q
        for atom in term["monomial"]:
            value = (value * env[str(atom)]) % q
        total = (total + value) % q
    return total


def tonelli_shanks(n: int, p: int) -> int:
    if n == 0:
        return 0
    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)

    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1

    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1

    m = s
    c = pow(z, q, p)
    t = pow(n, q, p)
    r = pow(n, (q + 1) // 2, p)

    while t != 1:
        i = 1
        t2 = pow(t, 2, p)
        while t2 != 1:
            t2 = pow(t2, 2, p)
            i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m = i
        c = (b * b) % p
        t = (t * c) % p
        r = (r * b) % p
    return r


def solve_modular_quadratic(a: int, b: int, c: int, q: int) -> list[int]:
    a %= q
    b %= q
    c %= q
    if a == 0:
        if b == 0:
            return []
        return [(-c * inverse(b, q)) % q]

    discriminant = (b * b - 4 * a * c) % q
    if pow(discriminant, (q - 1) // 2, q) != 1:
        return []
    sqrt_discriminant = tonelli_shanks(discriminant, q)
    denominator = inverse((2 * a) % q, q)
    return [
        ((-b + sqrt_discriminant) * denominator) % q,
        ((-b - sqrt_discriminant) * denominator) % q,
    ]


def sample_prime_order_group(q: int, rng: random.Random) -> tuple[int, int]:
    while True:
        k = rng.getrandbits(768)
        k |= 1 << 767
        if k % 2 != 0:
            k += 1
        p = k * q + 1
        if isPrime(p):
            break

    h = 2
    while True:
        g = pow(h, (p - 1) // q, p)
        if g > 1:
            return p, g
        h += 1


def transform_visible_rhs_to_python(rhs_text: str, q_symbol: str) -> str:
    expr = rhs_text.replace("^", "**")
    expr = re.sub(
        r"inv\(([A-Za-z]+)\(x\)\)",
        lambda match: f"pow({match.group(1)}, -1, {q_symbol})",
        expr,
    )
    expr = re.sub(r"([A-Za-z]+)\(x\)", lambda match: match.group(1), expr)
    expr = re.sub(
        r"inv\(([A-Za-z]+)\)",
        lambda match: f"pow({match.group(1)}, -1, {q_symbol})",
        expr,
    )
    return expr


def has_free_x(expr_text: str) -> bool:
    stripped = re.sub(r"inv\([A-Za-z]+\(x\)\)", "", expr_text)
    stripped = re.sub(r"[A-Za-z]+\(x\)", "", stripped)
    return bool(re.search(r"(?<![A-Za-z])x(?![A-Za-z])", stripped))


def sign_of_scalar(value: int) -> int:
    return -1 if value < 0 else 1


def sample_nonzero_mod_q(rng: random.Random, q: int) -> int:
    while True:
        value = rng.randrange(1, q)
        if value != 0:
            return value


def compute_signatures(
    messages: list[bytes],
    nonces: list[int],
    p: int,
    q: int,
    g: int,
    private_x: int,
) -> list[tuple[int, int]]:
    signatures: list[tuple[int, int]] = []
    for message, nonce in zip(messages, nonces):
        h = bytes_to_long(hashlib.sha256(message).digest()) % q
        r = pow(g, nonce, p) % q
        if r == 0:
            raise ValueError("Encountered zero r value")
        s = (inverse(nonce, q) * (h + private_x * r)) % q
        if s == 0:
            raise ValueError("Encountered zero s value")
        signatures.append((r, s))
    return signatures


def build_env_for_solver(challenge: dict[str, object]) -> dict[str, int]:
    q = int(challenge["q"])
    env = {name: value % q for name, value in challenge["constants"].items()}
    for source in challenge["inverse_sources"]:
        env[f"inv({source})"] = pow(env[source], -1, q)

    messages = [message.encode() for message in challenge["messages"]]
    signatures = [tuple(signature) for signature in challenge["signatures"]]
    for term_info, message, signature in zip(challenge["affine_terms"], messages, signatures):
        r, s = signature
        inv_s = inverse(s, q)
        w = (bytes_to_long(hashlib.sha256(message).digest()) * inv_s) % q
        v = (r * inv_s) % q
        env[term_info["intercept_name"]] = (term_info["intercept_sign"] * w) % q
        env[term_info["slope_name"]] = (term_info["slope_sign"] * v) % q
    return env


def verify_instance(challenge: dict[str, object], flag: bytes) -> None:
    q = int(challenge["q"])
    p = int(challenge["p"])
    g = int(challenge["g"])
    y = int(challenge["y"])
    env = build_env_for_solver(challenge)
    quadratic = challenge["quadratic_terms"]
    a = eval_formal_data(quadratic["square"], env, q)
    b = eval_formal_data(quadratic["linear"], env, q)
    c = eval_formal_data(quadratic["constant"], env, q)
    roots = solve_modular_quadratic(a, b, c, q)
    expected_x = bytes_to_long(flag)
    valid_roots = [root for root in roots if pow(g, root, p) == y]
    if expected_x not in valid_roots:
        raise ValueError("Solver verification failed to recover the private key")
    if long_to_bytes(expected_x) != flag:
        raise ValueError("Recovered bytes do not match the embedded flag")


def render_server_file(module_name: str, challenge: dict[str, object], flag: bytes, rhs_expr: str) -> str:
    constants = list(challenge["constants"].items())
    state_terms = challenge["affine_terms"][:-1]
    state_aliases = [term["alias_name"] for term in state_terms]
    messages = challenge["messages"]
    seed_nonces = challenge["seed_nonces"]
    recurrence_expr = server_expr_from_rhs(rhs_expr, state_aliases, [name for name, _ in constants], "self.q")

    state_setup = [f"        self.{alias} = {seed_nonces[index]}" for index, alias in enumerate(state_aliases)]
    constant_setup = [f"        self.{name} = {value}" for name, value in constants]
    constant_prints = [f'    print(f"  {name} = {{server.{name}}}")' for name, _ in constants]
    message_defs = [f'    msg{index} = b"{message}"' for index, message in enumerate(messages, start=1)]
    signature_assignments = [f'    r{index}, s{index} = server.sign(msg{index})' for index in range(1, len(messages) + 1)]
    signature_prints = []
    for index in range(1, len(messages) + 1):
        signature_prints.append(f'    print(f"Msg {index}: {{msg{index}.decode()}}")')
        signature_prints.append(f'    print(f"r{index} = {{r{index}}}")')
        signature_prints.append(f'    print(f"s{index} = {{s{index}}}\\n")')

    return "\n".join([
        "import hashlib",
        "import os",
        "from Crypto.Util.number import bytes_to_long, getPrime, isPrime",
        "",
        f"FLAG = {flag!r}",
        "",
        "class WeakDSAServer:",
        "    def __init__(self):",
        "        # Standard DSA group parameters",
        f"        self.q = {challenge['q']}",
        f"        self.p = {challenge['p']}",
        f"        self.g = {challenge['g']}",
        "",
        "        # Private key x, Public key y",
        "        self.x = bytes_to_long(FLAG)",
        f"        self.y = {challenge['y']}",
        "",
        "        # Generated state terms",
        *state_setup,
        "",
        "        # Other constants",
        *constant_setup,
        "",
        "        self.current_k = 0",
        "",
        "    def get_next_nonce(self):",
        "        \"\"\"Vulnerable Nonce Generator using a generated recurrence.\"\"\"",
        f"        self.current_k = ({recurrence_expr}) % self.q",
        *[f"        self.{state_aliases[i]} = self.{state_aliases[i + 1]}" for i in range(len(state_aliases) - 1)],
        f"        self.{state_aliases[-1]} = self.current_k",
        "        return self.current_k",
        "",
        "    def sign(self, message: bytes):",
        "        h = bytes_to_long(hashlib.sha256(message).digest()) % self.q",
        "        k = self.get_next_nonce()",
        "",
        "        r = pow(self.g, k, self.p) % self.q",
        "        k_inv = pow(k, -1, self.q)",
        "        s = (k_inv * (h + self.x * r)) % self.q",
        "        return (r, s)",
        "",
        "",
        "def main():",
        "    server = WeakDSAServer()",
        "    print(\"=== Vulnerable DSA Signing Service ===\")",
        "    print(f\"p = {server.p}\")",
        "    print(f\"q = {server.q}\")",
        "    print(f\"g = {server.g}\")",
        "    print(f\"y = {server.y}\")",
        "    print()",
        "    print(\"Other constants:\")",
        *constant_prints,
        "    print()",
        *message_defs,
        *signature_assignments,
        *signature_prints,
        "",
        "if __name__ == \"__main__\":",
        "    main()",
    ])


def render_solution_file(module_name: str, challenge: dict[str, object]) -> str:
    message_count = len(challenge["messages"])
    constant_lines = [f"{name} = {value}" for name, value in challenge["constants"].items()]
    msg_lines = [f"msg{index} = b\"{message}\"" for index, message in enumerate(challenge["messages"], start=1)]
    r_lines = [f"r{index} = {signature[0]}" for index, signature in enumerate(challenge["signatures"], start=1)]
    s_lines = [f"s{index} = {signature[1]}" for index, signature in enumerate(challenge["signatures"], start=1)]
    msg_list = ", ".join(f"msg{index}" for index in range(1, len(challenge["messages"]) + 1))
    r_list = ", ".join(f"r{index}" for index in range(1, len(challenge["messages"]) + 1))
    s_list = ", ".join(f"s{index}" for index in range(1, len(challenge["messages"]) + 1))
    return "\n".join([
        "from Crypto.Util.number import long_to_bytes, inverse",
        "",
        f"p = {challenge['p']}",
        f"q = {challenge['q']}",
        f"g = {challenge['g']}",
        f"y = {challenge['y']}",
        *constant_lines,
        "",
        *msg_lines,
        *r_lines,
        *s_lines,
        "",
        "import hashlib",
        f"msgs=[{msg_list}]",
        f"rs=[{r_list}]",
        f"ss=[{s_list}]",
        "hs=[int.from_bytes(hashlib.sha256(m).digest(),'big')%q for m in msgs]",
        "",
        "def tonelli(n,p):",
        "    assert pow(n,(p-1)//2,p)==1",
        "    if p%4==3:",
        "        return pow(n,(p+1)//4,p)",
        "    q1=p-1; s=0",
        "    while q1%2==0:",
        "        s+=1; q1//=2",
        "    z=2",
        "    while pow(z,(p-1)//2,p)!=p-1:",
        "        z+=1",
        "    m=s; c=pow(z,q1,p); t=pow(n,q1,p); r=pow(n,(q1+1)//2,p)",
        "    while t!=1:",
        "        i=1; tt=pow(t,2,p)",
        "        while tt!=1:",
        "            tt=pow(tt,2,p); i+=1",
        "        b=pow(c,1<<(m-i-1),p)",
        "        m=i; c=(b*b)%p; t=(t*c)%p; r=(r*b)%p",
        "    return r",
        "",
        f"w=[(hs[i]*inverse(ss[i],q))%q for i in range({message_count})]",
        f"v=[(rs[i]*inverse(ss[i],q))%q for i in range({message_count})]",
        "",
        "def eval_formal_data(terms, env, q):",
        "    total = 0",
        "    for term in terms:",
        "        value = int(term['coefficient']) % q",
        "        for atom in term['monomial']:",
        "            value = (value * env[str(atom)]) % q",
        "        total = (total + value) % q",
        "    return total",
        "",
        "def solve_modular_quadratic(a,b,c,q):",
        "    a %= q",
        "    b %= q",
        "    c %= q",
        "    if a == 0:",
        "        if b == 0:",
        "            return []",
        "        return [(-c * inverse(b, q)) % q]",
        "    discriminant = (b * b - 4 * a * c) % q",
        "    if pow(discriminant, (q - 1) // 2, q) != 1:",
        "        return []",
        "    sqrtD = tonelli(discriminant, q)",
        "    inv2a = inverse((2 * a) % q, q)",
        "    return [((-b + sqrtD) * inv2a) % q, ((-b - sqrtD) * inv2a) % q]",
        "",
        f"env = {{name: value % q for name, value in {{ {', '.join(f'{repr(name)}: {value}' for name, value in challenge['constants'].items())} }}.items()}}",
        *[f"env['inv({source})'] = pow(env['{source}'], -1, q)" for source in challenge["inverse_sources"]],
        f"for term_info, message, signature in zip({challenge['affine_terms']!r}, msgs, zip(rs, ss)):",
        "    r, s = signature",
        "    inv_s = inverse(s, q)",
        "    w = (int.from_bytes(hashlib.sha256(message).digest(), 'big') * inv_s) % q",
        "    v = (r * inv_s) % q",
        "    env[term_info['intercept_name']] = (term_info['intercept_sign'] * w) % q",
        "    env[term_info['slope_name']] = (term_info['slope_sign'] * v) % q",
        "",
        f"a = eval_formal_data({challenge['quadratic_terms']['square']!r}, env, q)",
        f"b = eval_formal_data({challenge['quadratic_terms']['linear']!r}, env, q)",
        f"c = eval_formal_data({challenge['quadratic_terms']['constant']!r}, env, q)",
        "roots = solve_modular_quadratic(a, b, c, q)",
        "",
        "for root in roots:",
        "    if pow(g, root, p) == y:",
        "        print(long_to_bytes(root))",
        "        break",
    ])


def build_challenge_instance(index: int, seed: int) -> tuple[str, dict[str, object], bytes, str]:
    rng = random.Random(seed ^ 0x5A5A5A5A)
    module_name = f"challenge_{index:03d}"

    while True:
        bundle = generate_formula(seed=seed, **GENERATOR_OPTIONS)
        lhs_text, rhs_text = bundle.equation.split(" = ", 1)
        if has_free_x(rhs_text):
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        q = bundle.modulus
        constants = {
            name: sample_nonzero_mod_q(rng, q)
            for name in bundle.other_constants
        }
        messages = [f"Message {{i}}: Give me the flag".format(i=i) for i in range(1, len(bundle.affine_terms) + 1)]
        seed_nonces = [sample_nonzero_mod_q(rng, q) for _ in range(len(bundle.affine_terms) - 1)]
        flag = f"FLAG{{currywurst_{rng.randrange(10000, 100000)}}}".encode()
        private_x = bytes_to_long(flag)
        if private_x >= q:
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        p, g = sample_prime_order_group(q, rng)
        y = pow(g, private_x, p)

        rhs_expr = transform_visible_rhs_to_python(rhs_text, "q")
        alias_names = [term.name for term in bundle.affine_terms]
        state = dict(zip(alias_names[:-1], seed_nonces))
        local_env = {**constants, **state, "q": q, "pow": pow}
        try:
            recurring_nonce = eval(rhs_expr, {}, local_env) % q
        except ValueError:
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        if recurring_nonce == 0:
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        nonces = seed_nonces + [recurring_nonce]
        try:
            signatures = compute_signatures([message.encode() for message in messages], nonces, p, q, g, private_x)
        except ValueError:
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        quadratic = quadratic_difference(bundle.lhs_quadratic, bundle.rhs_quadratic)
        challenge = {
            "name": module_name,
            "p": p,
            "q": q,
            "g": g,
            "y": y,
            "messages": messages,
            "signatures": signatures,
            "constants": constants,
            "other_constants": bundle.other_constants,
            "inverse_sources": [term.source for term in bundle.inverse_terms],
            "inverse_term_displays": [term.display for term in bundle.inverse_terms],
            "affine_definitions": [
                f"{term.name}(x) = {format_affine(term.intercept, term.slope)}"
                for term in bundle.affine_terms
            ],
            "affine_terms": [
                {
                    "alias_name": term.name,
                    "intercept_name": term.intercept.name,
                    "intercept_sign": sign_of_scalar(term.intercept.value),
                    "slope_name": term.slope.name,
                    "slope_sign": sign_of_scalar(term.slope.value),
                }
                for term in bundle.affine_terms
            ],
            "equation": bundle.equation,
            "multilinear_equation": bundle.multilinear_equation,
            "quadratic_form": bundle.quadratic_form,
            "quadratic_terms": {
                "constant": formal_to_data(quadratic[0]),
                "linear": formal_to_data(quadratic[1]),
                "square": formal_to_data(quadratic[2]),
            },
            "seed_nonces": seed_nonces,
            "withheld_alias_name": bundle.withheld_alias_name,
            "mult_inverse_alias_name": bundle.mult_inverse_alias_name,
        }

        try:
            verify_instance(challenge, flag)
        except ValueError:
            seed += 1
            rng.seed(seed ^ 0x5A5A5A5A)
            continue

        return module_name, challenge, flag, rhs_text


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[Path, Path, str]] = []

    for index in range(1, CHALLENGE_COUNT + 1):
        challenge_seed = SEED_START + index * SEED_STRIDE
        module_name, challenge, flag, rhs_text = build_challenge_instance(index, challenge_seed)
        server_path = OUTPUT_DIR / f"{module_name}_server.py"
        solution_path = OUTPUT_DIR / f"{module_name}_solution.py"
        write_text(server_path, render_server_file(module_name, challenge, flag, transform_visible_rhs_to_python(rhs_text, "self.q")))
        write_text(solution_path, render_solution_file(module_name, challenge))
        generated.append((server_path, solution_path, challenge["equation"]))

    print("Generated challenge pairs:")
    for server_path, solution_path, equation in generated:
        print(f"  {server_path.name}")
        print(f"  {solution_path.name}")
        print(f"  {equation}")
        print()

    print("Verifying solver output:")
    for _, solution_path, _ in generated:
        result = subprocess.run(
            [sys.executable, solution_path.name],
            cwd=OUTPUT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"  {solution_path.name}: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
