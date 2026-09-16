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

import generator as generator_module
from generator import FIELD_PRIME_BITS, display_field_value, format_affine, generate_formula, is_probable_prime

OUTPUT_DIR = Path(__file__).with_name("generated_challenges")
CHALLENGE_COUNT = 3
SEED_START = 789
SEED_STRIDE = 1000004
SAMPLED_GROUPS: dict[int, tuple[int, int]] = {}
MODULUS_SYMBOL = "__QMOD__"
RUNTIME_SEED_XOR = 0x5A5A5A5A

GENERATOR_OPTIONS = {
    "alias_count":                      5,
    "extra_terms":                      4,
    "complexity":                       "medium", # low medium high
    "direct_alias_product_rate":        0.5,
    "coefficient_rate":                 0.5,
    "raw_linear_terms_min":             1,
    "raw_linear_terms_max":             5,
    "other_constants_min":              1,
    "other_constants_max":              5,
    "constant_min_appearances":         3,
    "constant_min_product_appearances": 1,
    "inverse_rate":                     0.45,
    "inverse_min_appearances":          1,
    "inverse_min_product_appearances":  6,
    "free_x":                           False,
    "linear_part_min":                  None,
    "linear_part_max":                  None,
    "leaf_part_min":                    None,
    "leaf_part_max":                    None,
    "nested_linear_rate":               None,
    "nested_linear_scale_rate":         None,
    "combo_scale_rate":                 None,
    "compound_piece_rate":              None,
    "compound_piece_min":               None,
    "compound_piece_max":               None,
    "quadratic_depth":                  None,
    "core_depth":                       None,
    "constant_atom_rate":               None,
    "extra_constant_rate":              None,
    "mult_inverse":                     True,
}


def smallest_modular_representative(value: int, modulus: int) -> int:
    residue = value % modulus
    if residue > modulus // 2:
        return residue - modulus
    return residue


def formal_to_data(formal: dict[tuple[str, ...], int], modulus: int) -> list[dict[str, object]]:
    return [
        {"monomial": list(monomial), "coefficient": smallest_modular_representative(coefficient, modulus)}
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


def state_runtime_name(alias_name: str) -> str:
    return f"state_{alias_name}"


def constant_runtime_name(constant_name: str) -> str:
    return f"const_{constant_name}"


def server_expr_from_rhs(rhs_text: str, replacements: dict[str, str], q_symbol: str) -> str:
    expr = transform_visible_rhs_to_python(rhs_text, MODULUS_SYMBOL)
    for name, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        expr = re.sub(rf"\b{re.escape(name)}\b", replacement, expr)
    expr = expr.replace(MODULUS_SYMBOL, q_symbol)
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
    if q in SAMPLED_GROUPS:
        return SAMPLED_GROUPS[q]

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
            SAMPLED_GROUPS[q] = (p, g)
            return p, g
        h += 1


def sample_prime_modulus_for_seed(seed: int) -> int:
    rng = random.Random(seed)
    while True:
        candidate = rng.getrandbits(FIELD_PRIME_BITS)
        candidate |= 1 << (FIELD_PRIME_BITS - 1)
        candidate |= 1
        if is_probable_prime(candidate, rng):
            return candidate


def build_runtime_challenge(
    bundle,
    runtime_seed: int,
    flag_suffix: int,
    module_name: str,
    rhs_text: str,
) -> tuple[dict[str, object], bytes]:
    q = sample_prime_modulus_for_seed(runtime_seed)
    rng = random.Random(runtime_seed ^ RUNTIME_SEED_XOR)
    constants = {
        name: sample_nonzero_mod_q(rng, q)
        for name in bundle.other_constants
    }
    messages = [f"Message {{i}}: Give me the flag".format(i=i) for i in range(1, len(bundle.affine_terms) + 1)]
    seed_nonces = [sample_nonzero_mod_q(rng, q) for _ in range(len(bundle.affine_terms) - 1)]
    flag = f"FLAG{{currywurst_{flag_suffix}}}".encode()
    private_x = bytes_to_long(flag)
    if private_x >= q:
        raise ValueError("Flag is too large for sampled subgroup order")

    p, g = sample_prime_order_group(q, rng)
    y = pow(g, private_x, p)

    rhs_expr = transform_visible_rhs_to_python(rhs_text, MODULUS_SYMBOL)
    alias_names = [term.name for term in bundle.affine_terms]
    state = dict(zip(alias_names[:-1], seed_nonces))
    local_env = {**constants, **state, MODULUS_SYMBOL: q, "pow": pow}
    recurring_nonce = eval(rhs_expr, {}, local_env) % q
    if recurring_nonce == 0:
        raise ValueError("Runtime recurrence produced zero nonce")

    nonces = seed_nonces + [recurring_nonce]
    signatures = compute_signatures([message.encode() for message in messages], nonces, p, q, g, private_x)

    quadratic = quadratic_difference(bundle.lhs_quadratic, bundle.rhs_quadratic)
    challenge = {
        "name": module_name,
        "seed": runtime_seed,
        "flag_suffix": flag_suffix,
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
            "constant": formal_to_data(quadratic[0], q),
            "linear": formal_to_data(quadratic[1], q),
            "square": formal_to_data(quadratic[2], q),
        },
        "seed_nonces": seed_nonces,
        "withheld_alias_name": bundle.withheld_alias_name,
        "mult_inverse_alias_name": bundle.mult_inverse_alias_name,
    }
    return challenge, flag


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
    return -1 if display_field_value(value) < 0 else 1


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


def render_server_file(module_name: str, challenge: dict[str, object], flag: bytes, rhs_text: str) -> str:
    constants = list(challenge["constants"].keys())
    state_terms = challenge["affine_terms"][:-1]
    state_aliases = [term["alias_name"] for term in state_terms]
    messages = challenge["messages"]
    state_attrs = {alias: state_runtime_name(alias) for alias in state_aliases}
    constant_attrs = {name: constant_runtime_name(name) for name in constants}
    replacements = {
        **{alias: f"self.{attr_name}" for alias, attr_name in state_attrs.items()},
        **{name: f"self.{attr_name}" for name, attr_name in constant_attrs.items()},
    }
    recurrence_expr = server_expr_from_rhs(rhs_text, replacements, "self.group_q")

    state_setup = [f"        self.{state_attrs[alias]} = sample_nonzero_mod_q(runtime_rng, self.group_q)" for alias in state_aliases]
    constant_setup = [f"        self.{constant_attrs[name]} = sample_nonzero_mod_q(runtime_rng, self.group_q)" for name in constants]
    constant_prints = [f'    print(f"  {name} = {{challenge[\'constants\'][{name!r}]}}")' for name in constants]
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
        "import random",
        "from Crypto.Util.number import bytes_to_long, getPrime, isPrime",
        "",
        f"FLAG = {flag!r}",
        f"OTHER_CONSTANTS = {constants!r}",
        f"MESSAGES = {messages!r}",
        "",
        "FIELD_PRIME_BITS = 256",
        "",
        "def is_probable_prime(candidate, rng, rounds=16):",
        "    if candidate < 2:",
        "        return False",
        "    for small_prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31):",
        "        if candidate == small_prime:",
        "            return True",
        "        if candidate % small_prime == 0:",
        "            return False",
        "    d = candidate - 1",
        "    s = 0",
        "    while d % 2 == 0:",
        "        d //= 2",
        "        s += 1",
        "    for _ in range(rounds):",
        "        a = rng.randrange(2, candidate - 1)",
        "        x = pow(a, d, candidate)",
        "        if x in (1, candidate - 1):",
        "            continue",
        "        for _ in range(s - 1):",
        "            x = pow(x, 2, candidate)",
        "            if x == candidate - 1:",
        "                break",
        "        else:",
        "            return False",
        "    return True",
        "",
        "def sample_prime_modulus(seed):",
        "    rng = random.Random(seed)",
        "    while True:",
        "        candidate = rng.getrandbits(FIELD_PRIME_BITS)",
        "        candidate |= 1 << (FIELD_PRIME_BITS - 1)",
        "        candidate |= 1",
        "        if is_probable_prime(candidate, rng):",
        "            return candidate",
        "",
        "def sample_prime_order_group(q, rng):",
        "    while True:",
        "        k = rng.getrandbits(768)",
        "        k |= 1 << 767",
        "        if k % 2 != 0:",
        "            k += 1",
        "        p = k * q + 1",
        "        if isPrime(p):",
        "            break",
        "    h = 2",
        "    while True:",
        "        g = pow(h, (p - 1) // q, p)",
        "        if g > 1:",
        "            return p, g",
        "        h += 1",
        "",
        "def sample_nonzero_mod_q(rng, q):",
        "    while True:",
        "        value = rng.randrange(1, q)",
        "        if value != 0:",
        "            return value",
        "",
        "class WeakDSAServer:",
        "    def __init__(self):",
        "        # Standard DSA group parameters",
        "        runtime_rng = random.Random(os.urandom(96))",
        "        self.group_q = sample_prime_modulus(os.urandom(96))",
        "        self.group_p, self.generator_g = sample_prime_order_group(self.group_q, runtime_rng)",
        "",
        "        # Private key x, Public key y",
        "        self.private_x = bytes_to_long(FLAG)",
        "        self.public_y = pow(self.generator_g, self.private_x, self.group_p)",
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
        f"        self.current_k = ({recurrence_expr}) % self.group_q",
        *[f"        self.{state_attrs[state_aliases[i]]} = self.{state_attrs[state_aliases[i + 1]]}" for i in range(len(state_aliases) - 1)],
        f"        self.{state_attrs[state_aliases[-1]]} = self.current_k",
        "        return self.current_k",
        "",
        "    def sign(self, message: bytes):",
        "        h = bytes_to_long(hashlib.sha256(message).digest()) % self.group_q",
        "        k = self.get_next_nonce()",
        "",
        "        r = pow(self.generator_g, k, self.group_p) % self.group_q",
        "        k_inv = pow(k, -1, self.group_q)",
        "        s = (k_inv * (h + self.private_x * r)) % self.group_q",
        "        return (r, s)",
        "",
        "",
        "def export_public_challenge():",
        "    server = WeakDSAServer()",
        "    signatures = []",
        "    for message in MESSAGES:",
        "        signatures.append(server.sign(message.encode()))",
        "    return {",
        "        'p': server.group_p,",
        "        'q': server.group_q,",
        "        'g': server.generator_g,",
        "        'y': server.public_y,",
        "        'messages': list(MESSAGES),",
        "        'signatures': signatures,",
        f"        'constants': {{{', '.join(f'{name!r}: server.{constant_attrs[name]}' for name in constants)}}},",
        "    }",
        "",
        "def main():",
        "    challenge = export_public_challenge()",
        "    print(\"=== Vulnerable DSA Signing Service ===\")",
        "    print(f\"p = {challenge['p']}\")",
        "    print(f\"q = {challenge['q']}\")",
        "    print(f\"g = {challenge['g']}\")",
        "    print(f\"y = {challenge['y']}\")",
        "    print()",
        "    print(\"Other constants:\")",
        *constant_prints,
        "    print()",
        *[f"    msg{index} = challenge['messages'][{index - 1}].encode()" for index in range(1, len(messages) + 1)],
        *[f"    r{index}, s{index} = challenge['signatures'][{index - 1}]" for index in range(1, len(messages) + 1)],
        *signature_prints,
        "",
        "if __name__ == \"__main__\":",
        "    main()",
    ])


def render_solution_file(module_name: str, challenge: dict[str, object]) -> str:
    affine_env_assignments: list[str] = []
    for index, term_info in enumerate(challenge["affine_terms"]):
        affine_env_assignments.append(
            f"env['{term_info['intercept_name']}'] = ({term_info['intercept_sign']} * w[{index}]) % q"
        )
        affine_env_assignments.append(
            f"env['{term_info['slope_name']}'] = ({term_info['slope_sign']} * v[{index}]) % q"
        )

    return "\n".join([
        "import hashlib",
        "",
        "from Crypto.Util.number import long_to_bytes, inverse",
        "",
        f"import {module_name}_server as challenge_server",
        "",
        "public = challenge_server.export_public_challenge()",
        "p = public['p']",
        "q = public['q']",
        "g = public['g']",
        "y = public['y']",
        "msgs = [message.encode() for message in public['messages']]",
        "rs = [signature[0] for signature in public['signatures']]",
        "ss = [signature[1] for signature in public['signatures']]",
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
        "w=[(hs[i]*inverse(ss[i],q))%q for i in range(len(msgs))]",
        "v=[(rs[i]*inverse(ss[i],q))%q for i in range(len(msgs))]",
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
        "env = {name: value % q for name, value in public['constants'].items()}",
        *[f"env['inv({source})'] = pow(env['{source}'], -1, q)" for source in challenge["inverse_sources"]],
        *affine_env_assignments,
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
    module_name = f"challenge_{index:03d}"

    while True:
        generator_module.SAMPLED_FIELD_MODULUS = None
        bundle = generate_formula(seed=seed, **GENERATOR_OPTIONS)
        lhs_text, rhs_text = bundle.equation.split(" = ", 1)
        if has_free_x(rhs_text):
            seed += 1
            continue

        flag_suffix = 10000 + (seed % 90000)
        try:
            challenge, flag = build_runtime_challenge(bundle, seed, flag_suffix, module_name, rhs_text)
        except ValueError:
            seed += 1
            continue

        try:
            verify_instance(challenge, flag)
        except ValueError:
            seed += 1
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
        write_text(server_path, render_server_file(module_name, challenge, flag, rhs_text))
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
