from Crypto.Util.number import long_to_bytes, inverse

p = 87062437936393389468020945769077374486606105621754883410521322358565472128681733286237926941354039495746857227435989995857076314840252624218590371621114128510622288253980963200949174036469570719727982168947024123079042920155157547109298966043792571977737601733331233328369950223999420083018300151344726320593
q = 64929821218089736052093329003565926393393639381610099597349948188223645053909
g = 18573925846744227613332473269237840984420131590429948802557287034672454300508541987018824933528239717190104640200567179664427777135642652187758901280976867615224975432003154799334684830804493454357898076788986137783017219158451736436562667130618150393934478482577741796954911155392594163329856235432933483754
y = 42732044744277739069115553859570241368351589280507049166315366229575896177482009331018094015787695088165613094138688068755050510807324868836723535639215310775716470625725898390999119228709909893250088907578640440482069084202317065240605755185238991865336615684283006164164696571988754581559672511615833206363
e = 7032480303382669816850983107266071201810896148313947340206409980318655632542
i = 49616755265483364897624838225365254442680241556378574287538040609753735651428

msg1 = b"Message 1: Give me the flag"
msg2 = b"Message 2: Give me the flag"
r1 = 28628230908754420407677501003889248442925571092139361957309647293974355624669
r2 = 59221565102599532893420028900587818608511864284471445358283798732497781703515
s1 = 7992919704770299268736249199775655359781107004020861520410384216879779628622
s2 = 56101378650558299976341334545409712093278909094045741207359112560068893853538

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

env = {name: value % q for name, value in { 'e': 7032480303382669816850983107266071201810896148313947340206409980318655632542, 'i': 49616755265483364897624838225365254442680241556378574287538040609753735651428 }.items()}
for term_info, message, signature in zip([{'alias_name': 'u', 'intercept_name': 'a', 'intercept_sign': 1, 'slope_name': 'b', 'slope_sign': 1}, {'alias_name': 'f', 'intercept_name': 'c', 'intercept_sign': 1, 'slope_name': 'd', 'slope_sign': 1}], msgs, zip(rs, ss)):
    r, s = signature
    inv_s = inverse(s, q)
    w = (int.from_bytes(hashlib.sha256(message).digest(), 'big') * inv_s) % q
    v = (r * inv_s) % q
    env[term_info['intercept_name']] = (term_info['intercept_sign'] * w) % q
    env[term_info['slope_name']] = (term_info['slope_sign'] * v) % q

a = eval_formal_data([{'monomial': ['b', 'b'], 'coefficient': -1}, {'monomial': ['b', 'd'], 'coefficient': 1}], env, q)
b = eval_formal_data([{'monomial': ['a', 'b'], 'coefficient': -2}, {'monomial': ['a', 'd'], 'coefficient': 1}, {'monomial': ['b', 'c'], 'coefficient': 1}], env, q)
c = eval_formal_data([{'monomial': ['a', 'a'], 'coefficient': -1}, {'monomial': ['a', 'c'], 'coefficient': 1}, {'monomial': ['e', 'i'], 'coefficient': -1}, {'monomial': ['i'], 'coefficient': -1}], env, q)
roots = solve_modular_quadratic(a, b, c, q)

for root in roots:
    if pow(g, root, p) == y:
        print(long_to_bytes(root))
        break