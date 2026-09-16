import hashlib
import os
from Crypto.Util.number import bytes_to_long, getPrime, isPrime

FLAG = b'FLAG{currywurst_32178}'

class WeakDSAServer:
    def __init__(self):
        # Standard DSA group parameters
        self.q = 64929821218089736052093329003565926393393639381610099597349948188223645053909
        self.p = 87062437936393389468020945769077374486606105621754883410521322358565472128681733286237926941354039495746857227435989995857076314840252624218590371621114128510622288253980963200949174036469570719727982168947024123079042920155157547109298966043792571977737601733331233328369950223999420083018300151344726320593
        self.g = 18573925846744227613332473269237840984420131590429948802557287034672454300508541987018824933528239717190104640200567179664427777135642652187758901280976867615224975432003154799334684830804493454357898076788986137783017219158451736436562667130618150393934478482577741796954911155392594163329856235432933483754

        # Private key x, Public key y
        self.x = bytes_to_long(FLAG)
        self.y = 42732044744277739069115553859570241368351589280507049166315366229575896177482009331018094015787695088165613094138688068755050510807324868836723535639215310775716470625725898390999119228709909893250088907578640440482069084202317065240605755185238991865336615684283006164164696571988754581559672511615833206363

        # Generated state terms
        self.u = 10156189836282572441013015518740647516929616017316117914849080887826367200904

        # Other constants
        self.e = 7032480303382669816850983107266071201810896148313947340206409980318655632542
        self.i = 49616755265483364897624838225365254442680241556378574287538040609753735651428

        self.current_k = 0

    def get_next_nonce(self):
        """Vulnerable Nonce Generator using a generated recurrence."""
        self.current_k = (((self.i) - ((self.u)*((self.u - self.u - self.u)) + (self.i)*(-self.e)))*pow(self.u, -1, self.q)) % self.q
        self.u = self.current_k
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
    print()
    print("Other constants:")
    print(f"  e = {server.e}")
    print(f"  i = {server.i}")
    print()
    msg1 = b"Message 1: Give me the flag"
    msg2 = b"Message 2: Give me the flag"
    r1, s1 = server.sign(msg1)
    r2, s2 = server.sign(msg2)
    print(f"Msg 1: {msg1.decode()}")
    print(f"r1 = {r1}")
    print(f"s1 = {s1}\n")
    print(f"Msg 2: {msg2.decode()}")
    print(f"r2 = {r2}")
    print(f"s2 = {s2}\n")

if __name__ == "__main__":
    main()