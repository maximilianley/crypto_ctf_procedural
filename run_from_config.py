from __future__ import annotations

from generator import evaluate_correctness, format_affine, generate_formula

# Edit these flags line by line.
SEED                              = 789
ALIASES                           = 12
EXTRAS                            = 7
COMPLEXITY                        = "medium"
DIRECT_ALIAS_PRODUCT_RATE         = 0.5
COEFFICIENT_RATE                  = 0.5
RAW_LINEAR_TERMS_MIN              = 1
RAW_LINEAR_TERMS_MAX              = 5
OTHER_CONSTANTS_MIN               = 1
OTHER_CONSTANTS_MAX               = 5
CONSTANT_MIN_APPEARANCES          = 3
CONSTANT_MIN_PRODUCT_APPEARANCES  = 1
INVERSE_RATE                      = 0.45
INVERSE_MIN_APPEARANCES           = 1
INVERSE_MIN_PRODUCT_APPEARANCES   = 6
FREE_X                            = True
LINEAR_PART_MIN                   = None
LINEAR_PART_MAX                   = None
LEAF_PART_MIN                     = None
LEAF_PART_MAX                     = None
NESTED_LINEAR_RATE                = None
NESTED_LINEAR_SCALE_RATE          = None
COMBO_SCALE_RATE                  = None
COMPOUND_PIECE_RATE               = None
COMPOUND_PIECE_MIN                = None
COMPOUND_PIECE_MAX                = None
QUADRATIC_DEPTH                   = None
CORE_DEPTH                        = None
CONSTANT_ATOM_RATE                = None
EXTRA_CONSTANT_RATE               = None
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
        free_x=FREE_X,
        linear_part_min=LINEAR_PART_MIN,
        linear_part_max=LINEAR_PART_MAX,
        leaf_part_min=LEAF_PART_MIN,
        leaf_part_max=LEAF_PART_MAX,
        nested_linear_rate=NESTED_LINEAR_RATE,
        nested_linear_scale_rate=NESTED_LINEAR_SCALE_RATE,
        combo_scale_rate=COMBO_SCALE_RATE,
        compound_piece_rate=COMPOUND_PIECE_RATE,
        compound_piece_min=COMPOUND_PIECE_MIN,
        compound_piece_max=COMPOUND_PIECE_MAX,
        quadratic_depth=QUADRATIC_DEPTH,
        core_depth=CORE_DEPTH,
        constant_atom_rate=CONSTANT_ATOM_RATE,
        extra_constant_rate=EXTRA_CONSTANT_RATE,
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
