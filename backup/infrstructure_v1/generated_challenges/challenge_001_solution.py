from Crypto.Util.number import long_to_bytes, inverse

p = 127278856562137214612111581002510941163337900937174888243391013882732128026142209841071329010033195589332891265491896762587095154778135989644891507550687654564117317025767936350680344085651312901637408944418338118374069483644293385294217208507342580712407543491040660911096447165269336025245106808549386118323
q = 103281319250449290292758803283979570664449675451722265551336778434617156465449
g = 100759751363587042316253600739137827720537397217384356148078054142042563522656253914123050125144962068314387422165953965944984584344380353878138044028125254095666913913730710152764770198319508342495567595930565985874155539327992917137275513587264473945831363777219411209202376297592842250488718570205158266978
y = 35472858201520214284560958496620987857884849045905784403358287504142054735928738471373072601708757441309153020848126725621137008578071445393132955752873109125832026872809311608671952805862472522019304683261304534297682918719507099599486347874976105568068402979648751352105760413680302198655184351700216829712
e = 77070004907068957796009361332510535107823304592922027302307107748441679590984
i = 62182974612516472447522241647091603859556375678245672312839216954796417854880

msg1 = b"Message 1: Give me the flag"
msg2 = b"Message 2: Give me the flag"
r1 = 36850987978369300208536508203357946603583782365260048488261143122630312318507
r2 = 27583017914780366574848344090865199810696981467596772978851970527425539989018
s1 = 10812395572744657288824248237643046445219168307970162667775984281034925037156
s2 = 82585741234868915031502380842709550186031580149705045911931135283974866171390

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

env = {name: value % q for name, value in { 'e': 77070004907068957796009361332510535107823304592922027302307107748441679590984, 'i': 62182974612516472447522241647091603859556375678245672312839216954796417854880 }.items()}
for term_info, message, signature in zip([{'alias_name': 'u', 'intercept_name': 'a', 'intercept_sign': 1, 'slope_name': 'b', 'slope_sign': 1}, {'alias_name': 'f', 'intercept_name': 'c', 'intercept_sign': 1, 'slope_name': 'd', 'slope_sign': 1}], msgs, zip(rs, ss)):
    r, s = signature
    inv_s = inverse(s, q)
    w = (int.from_bytes(hashlib.sha256(message).digest(), 'big') * inv_s) % q
    v = (r * inv_s) % q
    env[term_info['intercept_name']] = (term_info['intercept_sign'] * w) % q
    env[term_info['slope_name']] = (term_info['slope_sign'] * v) % q

a = eval_formal_data([{'monomial': ['b', 'b'], 'coefficient': -103281319250449290292758803283979570664449675451722265551336778434617156465447}, {'monomial': ['b', 'd'], 'coefficient': 1}], env, q)
b = eval_formal_data([{'monomial': ['a', 'b'], 'coefficient': -103281319250449290292758803283979570664449675451722265551336778434617156465445}, {'monomial': ['a', 'd'], 'coefficient': 1}, {'monomial': ['b', 'c'], 'coefficient': 1}, {'monomial': ['b', 'e'], 'coefficient': -1}, {'monomial': ['b', 'i'], 'coefficient': -1}], env, q)
c = eval_formal_data([{'monomial': ['a', 'a'], 'coefficient': -103281319250449290292758803283979570664449675451722265551336778434617156465447}, {'monomial': ['a', 'c'], 'coefficient': 1}, {'monomial': ['a', 'e'], 'coefficient': -1}, {'monomial': ['a', 'i'], 'coefficient': -1}, {'monomial': ['i'], 'coefficient': -1}], env, q)
roots = solve_modular_quadratic(a, b, c, q)

for root in roots:
    if pow(g, root, p) == y:
        print(long_to_bytes(root))
        break