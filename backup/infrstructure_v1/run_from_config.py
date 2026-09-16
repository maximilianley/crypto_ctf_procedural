from __future__ import annotations

from generator import evaluate_correctness, format_affine, generate_formula

# Edit these flags line by line.
SEED                              = 7899
ALIASES                           = 2
EXTRAS                            = 0
COMPLEXITY                        = "low"
DIRECT_ALIAS_PRODUCT_RATE         = 0.0 # 0.95
COEFFICIENT_RATE                  = 0.1
RAW_LINEAR_TERMS_MIN              = 1
RAW_LINEAR_TERMS_MAX              = 1
OTHER_CONSTANTS_MIN               = 1
OTHER_CONSTANTS_MAX               = 1
CONSTANT_MIN_APPEARANCES          = 1
CONSTANT_MIN_PRODUCT_APPEARANCES  = 1
INVERSE_RATE                      = 0.3
INVERSE_MIN_APPEARANCES           = 1
INVERSE_MIN_PRODUCT_APPEARANCES   = 0
MULT_INVERSE                      = True


def main() -> None:
    bundle = generate_formula(
        seed=SEED,
        alias_count=ALIASES,
        extra_terms=EXTRAS,
        complexity=COMPLEXITY,
        direct_alias_product_rate=DIRECT_ALIAS_PRODUCT_RATE,
        coefficient_rate=COEFFICIENT_RATE,
        raw_linear_terms_min=RAW_LINEAR_TERMS_MIN,
        raw_linear_terms_max=RAW_LINEAR_TERMS_MAX,
        other_constants_min=OTHER_CONSTANTS_MIN,
        other_constants_max=OTHER_CONSTANTS_MAX,
        constant_min_appearances=CONSTANT_MIN_APPEARANCES,
        constant_min_product_appearances=CONSTANT_MIN_PRODUCT_APPEARANCES,
        inverse_rate=INVERSE_RATE,
        inverse_min_appearances=INVERSE_MIN_APPEARANCES,
        inverse_min_product_appearances=INVERSE_MIN_PRODUCT_APPEARANCES,
        mult_inverse=MULT_INVERSE,
    )
    assignment_lines, derived_affine_values, check_lines = evaluate_correctness(bundle, SEED)

    print(f"Modulus q = {bundle.modulus}")
    print()
    print("Affine terms:")
    for affine_term in bundle.affine_terms:
        print(f"  {affine_term.name}(x) = {format_affine(affine_term.intercept, affine_term.slope)}")
    print()
    print("Other constants:")
    for constant_name in bundle.other_constants:
        print(f"  {constant_name}")
    print()
    print("Inverse terms:")
    for inverse_term in bundle.inverse_terms:
        print(f"  {inverse_term.display}")
    print()
    print("Generated equation:")
    print(f"  {bundle.equation}")
    print()
    print("Compact multilinear form:")
    print(f"  {bundle.multilinear_equation}")
    print()
    print("Quadratic form:")
    print(f"  {bundle.quadratic_form}")
    print()
    print("Sampled values:")
    for line in assignment_lines:
        print(f"  {line}")
    print()
    print("Derived affine values:")
    for line in derived_affine_values:
        print(f"  {line}")
    print()
    print("Correctness check:")
    for line in check_lines:
        print(f"  {line}")
    print()
    print("Quadratic structure:")
    print("  hidden coefficients verify that this is quadratic in x")


if __name__ == "__main__":
    main()
