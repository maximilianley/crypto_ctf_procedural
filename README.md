# Quadratic DSA generation
This project implements a procedural CTF challenge generator for a cryptographic challenge.
The challenge is built around a flawed implementation of a DSA nonce generation.

DSA schemes, such as ECDSA, are used to generate private keys or to provide randomnes at system startup for later use. Vulnerabilities stem from weak randomness (for example too little or predictable seeds), or from easily reversible deterministic procedures. This specific challenge introduces such a deterministic nonce generation procedure, motivated by a Linear Congruential Generator. We expand on this idea by generating nonces based on a quadratic relationship between 3 or more previous nonces.

By using quadratic root finding techniques, such as the pq- or the ABC-formula adapted to prime modular fields, one can likewise trivially solve for the secret root x and extract the secret flag.

The purpose of this generator is to produce seemingly difficult generation schemes, while maintaining the quadratic characteristic ax²+bx+c = 0 mod q .