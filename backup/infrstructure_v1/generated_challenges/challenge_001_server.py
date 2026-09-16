import hashlib
import os
from Crypto.Util.number import bytes_to_long, getPrime, isPrime

FLAG = b'FLAG{currywurst_23337}'

class WeakDSAServer:
    def __init__(self):
        # Standard DSA group parameters
        self.q = 103281319250449290292758803283979570664449675451722265551336778434617156465449
        self.p = 127278856562137214612111581002510941163337900937174888243391013882732128026142209841071329010033195589332891265491896762587095154778135989644891507550687654564117317025767936350680344085651312901637408944418338118374069483644293385294217208507342580712407543491040660911096447165269336025245106808549386118323
        self.g = 100759751363587042316253600739137827720537397217384356148078054142042563522656253914123050125144962068314387422165953965944984584344380353878138044028125254095666913913730710152764770198319508342495567595930565985874155539327992917137275513587264473945831363777219411209202376297592842250488718570205158266978

        # Private key x, Public key y
        self.x = bytes_to_long(FLAG)
        self.y = 35472858201520214284560958496620987857884849045905784403358287504142054735928738471373072601708757441309153020848126725621137008578071445393132955752873109125832026872809311608671952805862472522019304683261304534297682918719507099599486347874976105568068402979648751352105760413680302198655184351700216829712

        # Generated state terms
        self.u = 88965406865504235407124998695370623222434713173366049810568670858819086251137

        # Other constants
        self.e = 77070004907068957796009361332510535107823304592922027302307107748441679590984
        self.i = 62182974612516472447522241647091603859556375678245672312839216954796417854880

        self.current_k = 0

    def get_next_nonce(self):
        """Vulnerable Nonce Generator using a generated recurrence."""
        self.current_k = (((self.i + (self.e)*(self.u) + (self.i)*(self.u)) - ((self.u)*((self.u + self.u))))*pow(self.u, -1, self.q)) % self.q
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