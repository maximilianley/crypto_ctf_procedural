import hashlib
import os
import random
from Crypto.Util.number import bytes_to_long, getPrime, isPrime

FLAG = b'FLAG{currywurst_40801}'
OTHER_CONSTANTS = ['v', 'w', 'y', 'z', 'aa']
MESSAGES = ['Message 1: Give me the flag', 'Message 2: Give me the flag', 'Message 3: Give me the flag', 'Message 4: Give me the flag', 'Message 5: Give me the flag']

FIELD_PRIME_BITS = 256

def is_probable_prime(candidate, rng, rounds=16):
    if candidate < 2:
        return False
    for small_prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31):
        if candidate == small_prime:
            return True
        if candidate % small_prime == 0:
            return False
    d = candidate - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = rng.randrange(2, candidate - 1)
        x = pow(a, d, candidate)
        if x in (1, candidate - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, candidate)
            if x == candidate - 1:
                break
        else:
            return False
    return True

def sample_prime_modulus(seed):
    rng = random.Random(seed)
    while True:
        candidate = rng.getrandbits(FIELD_PRIME_BITS)
        candidate |= 1 << (FIELD_PRIME_BITS - 1)
        candidate |= 1
        if is_probable_prime(candidate, rng):
            return candidate

def sample_prime_order_group(q, rng):
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

def sample_nonzero_mod_q(rng, q):
    while True:
        value = rng.randrange(1, q)
        if value != 0:
            return value

class WeakDSAServer:
    def __init__(self):
        # Standard DSA group parameters
        runtime_rng = random.Random(os.urandom(96))
        self.group_q = sample_prime_modulus(os.urandom(96))
        self.group_p, self.generator_g = sample_prime_order_group(self.group_q, runtime_rng)

        # Private key x, Public key y
        self.private_x = bytes_to_long(FLAG)
        self.public_y = pow(self.generator_g, self.private_x, self.group_p)

        # Generated state terms
        self.state_u = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.state_f = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.state_g = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.state_h = sample_nonzero_mod_q(runtime_rng, self.group_q)

        # Other constants
        self.const_v = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.const_w = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.const_y = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.const_z = sample_nonzero_mod_q(runtime_rng, self.group_q)
        self.const_aa = sample_nonzero_mod_q(runtime_rng, self.group_q)

        self.current_k = 0

    def get_next_nonce(self):
        self.current_k = (((((self.state_g - self.state_h + self.state_f) - (-self.const_w + (self.state_u - self.state_g + self.state_u - self.state_f) + self.state_u + (self.const_v - self.state_u))) + ((self.state_h)*(self.state_g) + (self.const_z*(((self.state_u - -self.const_y) + self.state_u + self.const_aa - self.state_g + self.state_h)))*(((self.state_h - self.const_aa) + (-self.const_z - -self.const_w - self.state_g) - self.state_h + (self.state_h + self.state_h - self.state_h))) + (self.const_z*((self.state_g - -self.const_y + self.state_f + self.state_u)) + (-self.const_y + -self.const_y - self.state_h + -self.const_y) - self.state_f)) + self.const_aa*(((self.const_w*((-self.const_z + (self.state_u - self.state_h - self.state_h) + self.state_h - self.state_u + (self.state_g - self.state_h))) - self.state_h - self.const_aa - self.state_h) + (self.state_g - -self.const_z + (self.const_v - self.state_g - self.state_h) + self.state_g))) + self.const_w*(((self.state_g)*(self.state_g) + ((self.state_h - self.state_h + (-self.const_y - self.state_g - self.state_h) - (self.state_g + self.state_f - -self.const_z - self.state_g)))**2 + ((self.state_h + self.state_g + self.state_g + self.state_g) - self.const_z*((self.state_f + self.state_h)) + self.state_f + self.const_aa) - ((self.state_g + (self.state_u - self.state_f + -self.const_y) - self.state_h))*(self.const_y*((self.const_aa - self.state_u + self.const_z*((self.state_u - self.state_u + self.state_g)) - self.state_f))))) + self.const_z*((self.const_v*((self.state_u + (self.state_u + self.state_g - self.state_h - self.state_g) + self.state_g)) + self.state_u + self.state_g)) + (pow(self.const_v, -1, self.group_q))*(self.state_f) + (pow(self.const_v, -1, self.group_q))*(self.const_aa) + (pow(self.const_v, -1, self.group_q))*(-self.const_w) + (self.state_g)*(pow(self.const_w, -1, self.group_q)) + (pow(self.const_w, -1, self.group_q))*(self.state_h) + (-self.const_y)*(pow(self.const_w, -1, self.group_q)) + (pow(self.const_w, -1, self.group_q))*(self.state_g) + (pow(self.const_y, -1, self.group_q))*(self.state_u) + (pow(self.const_y, -1, self.group_q))*(self.state_f) + (self.const_v)*(pow(self.const_y, -1, self.group_q)) + (self.state_g)*(pow(self.const_y, -1, self.group_q)) + (pow(self.const_y, -1, self.group_q))*(-self.const_w)) - ((self.state_u)*((self.state_g + self.state_h + self.const_z*(self.const_y*((self.state_g + self.const_v*((self.state_f - self.state_g + self.state_u + self.state_g)) - (self.state_f - -self.const_w - -self.const_w)))))) + (self.state_h)*(self.state_u) + (self.const_aa*(((-self.const_y + self.state_h - (self.state_h - self.state_f + self.state_u - self.state_u)) + self.state_h + self.const_v*((self.state_u + (self.state_g + self.state_u + self.state_f - self.const_v) - self.state_h - self.const_v - -self.const_y)) + (self.const_w*((self.state_u - self.state_f + -self.const_w + self.state_g)) + self.const_w*((self.state_f - self.state_f)) - self.state_g + -self.const_z))) - ((self.const_z*((-self.const_w + self.state_h)) - -self.const_y - (self.state_u - self.const_v + self.state_h - self.state_u) - self.state_f))*((self.const_z*((self.state_f + self.state_u)) - self.state_g - self.const_y*((self.state_g + -self.const_y + self.state_g + -self.const_z)) + self.const_aa))) + (-self.const_z)*(pow(self.const_v, -1, self.group_q)) + (self.state_h)*(pow(self.const_v, -1, self.group_q)) + (pow(self.const_v, -1, self.group_q))*(self.state_h) + (-self.const_y)*(pow(self.const_w, -1, self.group_q)) + (pow(self.const_w, -1, self.group_q))*(self.state_h) + (self.const_v)*(pow(self.const_y, -1, self.group_q))))*pow(self.state_h, -1, self.group_q)) % self.group_q
        self.state_u = self.state_f
        self.state_f = self.state_g
        self.state_g = self.state_h
        self.state_h = self.current_k
        return self.current_k

    def sign(self, message: bytes):
        h = bytes_to_long(hashlib.sha256(message).digest()) % self.group_q
        k = self.get_next_nonce()

        r = pow(self.generator_g, k, self.group_p) % self.group_q
        k_inv = pow(k, -1, self.group_q)
        s = (k_inv * (h + self.private_x * r)) % self.group_q
        return (r, s)


def export_public_challenge():
    server = WeakDSAServer()
    signatures = []
    for message in MESSAGES:
        signatures.append(server.sign(message.encode()))
    return {
        'p': server.group_p,
        'q': server.group_q,
        'g': server.generator_g,
        'y': server.public_y,
        'messages': list(MESSAGES),
        'signatures': signatures,
        'constants': {'v': server.const_v, 'w': server.const_w, 'y': server.const_y, 'z': server.const_z, 'aa': server.const_aa},
    }

def main():
    challenge = export_public_challenge()
    print("=== Vulnerable DSA Signing Service ===")
    print(f"p = {challenge['p']}")
    print(f"q = {challenge['q']}")
    print(f"g = {challenge['g']}")
    print(f"y = {challenge['y']}")
    print()
    print("Other constants:")
    print(f"  v = {challenge['constants']['v']}")
    print(f"  w = {challenge['constants']['w']}")
    print(f"  y = {challenge['constants']['y']}")
    print(f"  z = {challenge['constants']['z']}")
    print(f"  aa = {challenge['constants']['aa']}")
    print()
    msg1 = challenge['messages'][0].encode()
    msg2 = challenge['messages'][1].encode()
    msg3 = challenge['messages'][2].encode()
    msg4 = challenge['messages'][3].encode()
    msg5 = challenge['messages'][4].encode()
    r1, s1 = challenge['signatures'][0]
    r2, s2 = challenge['signatures'][1]
    r3, s3 = challenge['signatures'][2]
    r4, s4 = challenge['signatures'][3]
    r5, s5 = challenge['signatures'][4]
    print(f"Msg 1: {msg1.decode()}")
    print(f"r1 = {r1}")
    print(f"s1 = {s1}\n")
    print(f"Msg 2: {msg2.decode()}")
    print(f"r2 = {r2}")
    print(f"s2 = {s2}\n")
    print(f"Msg 3: {msg3.decode()}")
    print(f"r3 = {r3}")
    print(f"s3 = {s3}\n")
    print(f"Msg 4: {msg4.decode()}")
    print(f"r4 = {r4}")
    print(f"s4 = {s4}\n")
    print(f"Msg 5: {msg5.decode()}")
    print(f"r5 = {r5}")
    print(f"s5 = {s5}\n")

if __name__ == "__main__":
    main()