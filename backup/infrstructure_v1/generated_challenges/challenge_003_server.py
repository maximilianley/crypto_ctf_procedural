import hashlib
import os
from Crypto.Util.number import bytes_to_long, getPrime, isPrime

FLAG = b'FLAG{currywurst_44953}'

class WeakDSAServer:
    def __init__(self):
        # Standard DSA group parameters
        self.q = 104053065830251340195193881869769444884361334008159803367115665382491127002311
        self.p = 111523747684706653720726800589364486979289752534844265570838205589174656221696641689533409986396243364859737065614129818242207316561646133528257900492817189145821087715007818777874949632036255022887274946944217473187086003899838294337994016729989858972645171426908665853110961527564636948381270073064376454697
        self.g = 2213308811181584198753895619158623118228979915538539226869319017346452197468430708388629390247274001090783546192258407898381934923429717846670550314208309520818891200455246224118149111110313410502703196921073220986860378376587542558346920913310219327606572409855021766646594563356503737603925193764595860249

        # Private key x, Public key y
        self.x = bytes_to_long(FLAG)
        self.y = 99530829821932348965440405885385198526192829953990283280814147233553619084959233084075981189267905705086973381785075061488970400396417775899254778696392375387919936074380969377315671325065529532867664606530529260016759274805590579718796622871891230011918321888677991148997139967499200746145304769270160933985

        # Generated state terms
        self.u = 23821287958021533422791078372536090971774987593182658746313056767425566094367

        # Other constants
        self.e = 57943178204989118490708420518780617533503627117048564199183375581311066050483
        self.i = 3482710630822545627898003517711507677366723214741764107098939363522947305019

        self.current_k = 0

    def get_next_nonce(self):
        """Vulnerable Nonce Generator using a generated recurrence."""
        self.current_k = (((self.i) - (((self.u - (self.u - self.u - self.u) - self.u))**2 + (-self.e)*(self.i)))*pow(self.u, -1, self.q)) % self.q
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