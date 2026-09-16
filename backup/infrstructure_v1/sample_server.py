import hashlib
import os
from Crypto.Util.number import bytes_to_long, getPrime, isPrime

# FLAG = b"CTF{l1n34r_n0nc3_r3l4t10n5h1p_br34k5_d54!}"
FLAG = b"FLAG{sd98vs9e334f}"

class WeakDSAServer:
    def __init__(self):
        # Standard DSA group parameters
        self.q = getPrime(256)
        self.p = getPrime(1024)
        #while (self.p - 1) % self.q != 0:
        #    self.p = getPrime(1024)
        while True:
            # 1024 bits total - 256 bits for q = 768 bits for k (96 bytes)
            k = bytes_to_long(os.urandom(96))
            
            # Ensure k is even so (k * q + 1) is odd, and ensure p hits 1024 bits
            k |= 1 << 767
            if k % 2 != 0:
                k += 1

            self.p = k * self.q + 1

            # Check if p is prime
            if isPrime(self.p):
                break
        
        # Generator g of order q mod p
        h = 2
        while True:
            self.g = pow(h, (self.p - 1) // self.q, self.p)
            if self.g > 1:
                break
            h += 1
            
        # Private key x, Public key y
        self.x = bytes_to_long(FLAG)
        assert self.x < self.q, "Flag is too long for the sub-group size!"
        self.y = pow(self.g, self.x, self.p)
        
        # Linear Nonce generator parameters (k2 = a*k1 + b mod q)
        self.a = bytes_to_long(os.urandom(16))
        self.b = bytes_to_long(os.urandom(16))
        self.last2_k = bytes_to_long(os.urandom(32)) % self.q
        self.last_k = bytes_to_long(os.urandom(32)) % self.q
        self.current_k = 0

    def get_next_nonce(self):
        """Vulnerable Nonce Generator using a known linear relation."""
        self.current_k = (self.a * pow(self.last2_k, 2, self.q) - self.b*self.last_k) % self.q
        self.last2_k = self.last_k
        self.last_k = self.current_k
        return self.current_k

    def sign(self, message: bytes):
        h = bytes_to_long(hashlib.sha256(message).digest()) % self.q
        k = self.get_next_nonce()
        
        r = pow(self.g, k, self.p) % self.q
        k_inv = pow(k, -1, self.q)
        s = (k_inv * (h + self.x * r)) % self.q
        return (r, s)

def main():
    server = WeakDSAServer()
    print("=== Vulnerable DSA Signing Service ===")
    print(f"p = {server.p}")
    print(f"q = {server.q}")
    print(f"g = {server.g}")
    print(f"y = {server.y}")
    print(f"Linear Nonce Multiplier (a) = {server.a}")
    print(f"Linear Nonce Increment  (b) = {server.b}\n")

    msg1 = b"Message 1: Give me the flag"
    msg2 = b"Message 2: Give me the flag"
    msg3 = b"Message 3: Give me the flag"

    r1, s1 = server.sign(msg1)
    r2, s2 = server.sign(msg2)
    r3, s3 = server.sign(msg3)

    print(f"Msg 1: {msg1.decode()}")
    print(f"r1 = {r1}")
    print(f"s1 = {s1}\n")

    print(f"Msg 2: {msg2.decode()}")
    print(f"r2 = {r2}")
    print(f"s2 = {s2}\n")
    
    print(f"Msg 3: {msg3.decode()}")
    print(f"r3 = {r3}")
    print(f"s3 = {s3}\n")

if __name__ == "__main__":
    main()