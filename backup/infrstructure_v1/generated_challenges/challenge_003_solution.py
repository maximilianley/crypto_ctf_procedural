from Crypto.Util.number import long_to_bytes, inverse

p = 111523747684706653720726800589364486979289752534844265570838205589174656221696641689533409986396243364859737065614129818242207316561646133528257900492817189145821087715007818777874949632036255022887274946944217473187086003899838294337994016729989858972645171426908665853110961527564636948381270073064376454697
q = 104053065830251340195193881869769444884361334008159803367115665382491127002311
g = 2213308811181584198753895619158623118228979915538539226869319017346452197468430708388629390247274001090783546192258407898381934923429717846670550314208309520818891200455246224118149111110313410502703196921073220986860378376587542558346920913310219327606572409855021766646594563356503737603925193764595860249
y = 99530829821932348965440405885385198526192829953990283280814147233553619084959233084075981189267905705086973381785075061488970400396417775899254778696392375387919936074380969377315671325065529532867664606530529260016759274805590579718796622871891230011918321888677991148997139967499200746145304769270160933985
e = 57943178204989118490708420518780617533503627117048564199183375581311066050483
i = 3482710630822545627898003517711507677366723214741764107098939363522947305019

msg1 = b"Message 1: Give me the flag"
msg2 = b"Message 2: Give me the flag"
r1 = 34627893041010716408393344902580829978422422258947336360925508993637306126728
r2 = 30312347467507134872419396932736887670942388958495817911942190539354746458180
s1 = 20977582862640786507673719369383834471482056782710466999016183582943959036467
s2 = 63408851900759022309085698336234949686332773050005304447257136375289269585212

import hashlib
msgs=[msg1, msg2]
rs=[r1, r2]
ss=[s1, s2]
hs=[int.from_bytes(hashlib.sha256(m).digest(),'big')%q for m in msgs]

def tonelli(n,p):
    assert pow(n,(p-1)//2,p)==1
    if p%4==3:
        return pow(n,(p+1)//4,p)
    q1=p-1; s=0
    while q1%2==0:
        s+=1; q1//=2
    z=2
    while pow(z,(p-1)//2,p)!=p-1:
        z+=1
    m=s; c=pow(z,q1,p); t=pow(n,q1,p); r=pow(n,(q1+1)//2,p)
    while t!=1:
        i=1; tt=pow(t,2,p)
        while tt!=1:
            tt=pow(tt,2,p); i+=1
        b=pow(c,1<<(m-i-1),p)
        m=i; c=(b*b)%p; t=(t*c)%p; r=(r*b)%p
    return r

w=[(hs[i]*inverse(ss[i],q))%q for i in range(2)]
v=[(rs[i]*inverse(ss[i],q))%q for i in range(2)]

def eval_formal_data(terms, env, q):
    total = 0
    for term in terms:
        value = int(term['coefficient']) % q
        for atom in term['monomial']:
            value = (value * env[str(atom)]) % q
        total = (total + value) % q
    return total

def solve_modular_quadratic(a,b,c,q):
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
    sqrtD = tonelli(discriminant, q)
    inv2a = inverse((2 * a) % q, q)
    return [((-b + sqrtD) * inv2a) % q, ((-b - sqrtD) * inv2a) % q]

env = {name: value % q for name, value in { 'e': 57943178204989118490708420518780617533503627117048564199183375581311066050483, 'i': 3482710630822545627898003517711507677366723214741764107098939363522947305019 }.items()}
for term_info, message, signature in zip([{'alias_name': 'u', 'intercept_name': 'a', 'intercept_sign': 1, 'slope_name': 'b', 'slope_sign': 1}, {'alias_name': 'f', 'intercept_name': 'c', 'intercept_sign': 1, 'slope_name': 'd', 'slope_sign': 1}], msgs, zip(rs, ss)):
    r, s = signature
    inv_s = inverse(s, q)
    w = (int.from_bytes(hashlib.sha256(message).digest(), 'big') * inv_s) % q
    v = (r * inv_s) % q
    env[term_info['intercept_name']] = (term_info['intercept_sign'] * w) % q
    env[term_info['slope_name']] = (term_info['slope_sign'] * v) % q

a = eval_formal_data([{'monomial': ['b', 'b'], 'coefficient': -104053065830251340195193881869769444884361334008159803367115665382491127002310}, {'monomial': ['b', 'd'], 'coefficient': 1}], env, q)
b = eval_formal_data([{'monomial': ['a', 'b'], 'coefficient': -104053065830251340195193881869769444884361334008159803367115665382491127002309}, {'monomial': ['a', 'd'], 'coefficient': 1}, {'monomial': ['b', 'c'], 'coefficient': 1}], env, q)
c = eval_formal_data([{'monomial': ['a', 'a'], 'coefficient': -104053065830251340195193881869769444884361334008159803367115665382491127002310}, {'monomial': ['a', 'c'], 'coefficient': 1}, {'monomial': ['e', 'i'], 'coefficient': -1}, {'monomial': ['i'], 'coefficient': -1}], env, q)
roots = solve_modular_quadratic(a, b, c, q)

for root in roots:
    if pow(g, root, p) == y:
        print(long_to_bytes(root))
        break