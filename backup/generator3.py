from __future__ import annotations

import argparse
import random
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction


CoeffTriple = tuple[int, int, int]
Monomial = tuple[str, ...]
FormalPolynomial = dict[Monomial, int]
QuadraticPolynomial = tuple[FormalPolynomial, FormalPolynomial, FormalPolynomial]
SYMBOL_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
FUNCTION_NAMES = ("u", "f", "g", "h", "p", "q", "r", "s", "t", "m", "n")
CORRECTNESS_SAMPLE_BOUND = 2**64


@dataclass(frozen=True)
class Scalar:
	name: str
	value: int


@dataclass(frozen=True)
class AffineTerm:
	name: str
	intercept: Scalar
	slope: Scalar


@dataclass(frozen=True)
class InverseTerm:
	source: str
	display: str
	symbol: Scalar


@dataclass(frozen=True)
class Expr:
	text: str
	coeffs: CoeffTriple
	formal: FormalPolynomial
	quadratic: QuadraticPolynomial


@dataclass(frozen=True)
class FormulaBundle:
	affine_terms: list[AffineTerm]
	inverse_terms: list[InverseTerm]
	other_constants: list[str]
	equation: str
	multilinear_equation: str
	quadratic_form: str
	coeffs: CoeffTriple
	lhs_formal: FormalPolynomial
	rhs_formal: FormalPolynomial
	lhs_quadratic: QuadraticPolynomial
	rhs_quadratic: QuadraticPolynomial


@dataclass(frozen=True)
class ComplexityProfile:
	linear_part_range: tuple[int, int]
	leaf_part_range: tuple[int, int]
	nested_linear_rate: float
	nested_linear_scale_rate: float
	combo_scale_rate: float
	compound_piece_rate: float
	compound_piece_range: tuple[int, int]
	quadratic_depth: int
	core_depth: int
	constant_atom_rate: float
	extra_constant_rate: float


COMPLEXITY_PRESETS: dict[str, ComplexityProfile] = {
	"low": ComplexityProfile(
		linear_part_range=(2, 3),
		leaf_part_range=(2, 3),
		nested_linear_rate=0.12,
		nested_linear_scale_rate=0.35,
		combo_scale_rate=0.20,
		compound_piece_rate=0.10,
		compound_piece_range=(2, 2),
		quadratic_depth=1,
		core_depth=1,
		constant_atom_rate=0.15,
		extra_constant_rate=0.30,
	),
	"medium": ComplexityProfile(
		linear_part_range=(3, 5),
		leaf_part_range=(2, 4),
		nested_linear_rate=0.35,
		nested_linear_scale_rate=0.70,
		combo_scale_rate=0.50,
		compound_piece_rate=0.45,
		compound_piece_range=(2, 4),
		quadratic_depth=2,
		core_depth=2,
		constant_atom_rate=0.25,
		extra_constant_rate=0.20,
	),
	"high": ComplexityProfile(
		linear_part_range=(4, 6),
		leaf_part_range=(3, 5),
		nested_linear_rate=0.55,
		nested_linear_scale_rate=0.80,
		combo_scale_rate=0.65,
		compound_piece_rate=0.65,
		compound_piece_range=(3, 5),
		quadratic_depth=3,
		core_depth=3,
		constant_atom_rate=0.30,
		extra_constant_rate=0.12,
	),
}


def add_coeffs(left: CoeffTriple, right: CoeffTriple) -> CoeffTriple:
	return (
		left[0] + right[0],
		left[1] + right[1],
		left[2] + right[2],
	)


def scale_coeffs(coeffs: CoeffTriple, factor: int) -> CoeffTriple:
	return (coeffs[0] * factor, coeffs[1] * factor, coeffs[2] * factor)


def multiply_linear(left: CoeffTriple, right: CoeffTriple) -> CoeffTriple:
	_, left_x, left_c = left
	_, right_x, right_c = right
	return (
		left_x * right_x,
		left_x * right_c + left_c * right_x,
		left_c * right_c,
	)


def normalize_monomial(parts: list[str]) -> Monomial:
	return tuple(sorted(parts, key=atom_sort_key))


def atom_sort_key(atom: str) -> tuple[int, str]:
	if atom == "x":
		return (2, atom)
	if atom in FUNCTION_NAMES or atom.endswith("(x)"):
		return (1, atom)
	return (0, atom)


def add_formal(left: FormalPolynomial, right: FormalPolynomial) -> FormalPolynomial:
	result: defaultdict[Monomial, int] = defaultdict(int)
	for monomial, coefficient in left.items():
		result[monomial] += coefficient
	for monomial, coefficient in right.items():
		result[monomial] += coefficient
	return {monomial: coefficient for monomial, coefficient in result.items() if coefficient}


def scale_formal(formal: FormalPolynomial, factor: int) -> FormalPolynomial:
	if factor == 1:
		return dict(formal)
	return {monomial: coefficient * factor for monomial, coefficient in formal.items() if coefficient * factor}


def multiply_formal(left: FormalPolynomial, right: FormalPolynomial) -> FormalPolynomial:
	result: defaultdict[Monomial, int] = defaultdict(int)
	for left_monomial, left_coefficient in left.items():
		for right_monomial, right_coefficient in right.items():
			monomial = normalize_monomial(list(left_monomial) + list(right_monomial))
			result[monomial] += left_coefficient * right_coefficient
	return {monomial: coefficient for monomial, coefficient in result.items() if coefficient}


def atom_formal(atom: str, coefficient: int = 1) -> FormalPolynomial:
	return {(atom,): coefficient}


def monomial_formal(atoms: list[str], coefficient: int = 1) -> FormalPolynomial:
	return {normalize_monomial(atoms): coefficient}


def format_monomial(monomial: Monomial) -> str:
	counts: dict[str, int] = {}
	ordered_atoms: list[str] = []
	for atom in monomial:
		if atom not in counts:
			ordered_atoms.append(atom)
		counts[atom] = counts.get(atom, 0) + 1

	pieces: list[str] = []
	for atom in ordered_atoms:
		count = counts[atom]
		if count == 1:
			pieces.append(atom)
		else:
			pieces.append(f"{atom}^{count}")
	return "*".join(pieces)


def format_formal_polynomial(formal: FormalPolynomial) -> str:
	if not formal:
		return "0"

	def sort_key(item: tuple[Monomial, int]) -> tuple[int, str]:
		monomial, _ = item
		return (len(monomial), format_monomial(monomial))

	pieces: list[str] = []
	for index, (monomial, coefficient) in enumerate(sorted(formal.items(), key=sort_key)):
		magnitude = abs(coefficient)
		body = format_monomial(monomial)
		if body == "":
			term = str(magnitude)
		elif magnitude == 1:
			term = body
		else:
			term = f"{magnitude}{body}"

		if coefficient < 0:
			pieces.append(f"- {term}" if index else f"-{term}")
		else:
			pieces.append(f"+ {term}" if index else term)
	return " ".join(pieces)


def source_label_from_name(name: str) -> str:
	if name.endswith("(x)"):
		return name[:-3]
	return name


def zero_quadratic() -> QuadraticPolynomial:
	return ({}, {}, {})


def add_quadratic(left: QuadraticPolynomial, right: QuadraticPolynomial) -> QuadraticPolynomial:
	return (
		add_formal(left[0], right[0]),
		add_formal(left[1], right[1]),
		add_formal(left[2], right[2]),
	)


def scale_quadratic(quadratic: QuadraticPolynomial, factor: int) -> QuadraticPolynomial:
	return (
		scale_formal(quadratic[0], factor),
		scale_formal(quadratic[1], factor),
		scale_formal(quadratic[2], factor),
	)


def multiply_linear_quadratic(left: QuadraticPolynomial, right: QuadraticPolynomial) -> QuadraticPolynomial:
	result = [defaultdict(int), defaultdict(int), defaultdict(int)]
	for left_degree, left_formal in enumerate(left):
		for right_degree, right_formal in enumerate(right):
			degree = left_degree + right_degree
			if degree > 2:
				continue
			product = multiply_formal(left_formal, right_formal)
			for monomial, coefficient in product.items():
				result[degree][monomial] += coefficient
	return tuple(
		{monomial: coefficient for monomial, coefficient in degree_terms.items() if coefficient}
		for degree_terms in result
	)


def sum_quadratic(terms: list[Expr]) -> QuadraticPolynomial:
	quadratic = zero_quadratic()
	for term in terms:
		quadratic = add_quadratic(quadratic, term.quadratic)
	return quadratic


def format_quadratic_term(coefficient: FormalPolynomial, suffix: str) -> str:
	formatted = format_formal_polynomial(coefficient)
	if formatted == "0":
		return ""
	if suffix == "":
		return formatted
	if formatted == "1":
		return suffix
	if formatted == "-1":
		return f"-{suffix}"
	if " " in formatted:
		return f"({formatted})*{suffix}"
	return f"{formatted}*{suffix}"


def format_quadratic_form(quadratic: QuadraticPolynomial) -> str:
	constant, linear, square = quadratic
	parts = [
		format_quadratic_term(square, "x^2"),
		format_quadratic_term(linear, "x"),
		format_quadratic_term(constant, ""),
	]
	pieces: list[str] = []
	for part in parts:
		if not part:
			continue
		if not pieces:
			pieces.append(part)
		elif part.startswith("-"):
			pieces.append(f"- {part[1:].lstrip()}")
		else:
			pieces.append(f"+ {part}")
	if not pieces:
		return "0 = 0"
	return f"{' '.join(pieces)} = 0"


def evaluate_formal(formal: FormalPolynomial, assignments: dict[str, int]) -> int:
	total: Fraction | int = 0
	for monomial, coefficient in formal.items():
		term_value: Fraction | int = coefficient
		for atom in monomial:
			term_value *= assignments[atom]
		total += term_value
	return total


def evaluate_quadratic(quadratic: QuadraticPolynomial, assignments: dict[str, int], x_value: int) -> int:
	constant, linear, square = quadratic
	return (
		evaluate_formal(constant, assignments)
		+ evaluate_formal(linear, assignments) * x_value
		+ evaluate_formal(square, assignments) * x_value * x_value
	)


def sample_nonzero_integer(rng: random.Random) -> int:
	while True:
		value = sample_integer(rng)
		if value != 0:
			return value


def sample_large_nonzero_integer(rng: random.Random) -> int:
	while True:
		value = rng.randint(-CORRECTNESS_SAMPLE_BOUND, CORRECTNESS_SAMPLE_BOUND)
		if value != 0:
			return value


def sample_symbol_assignments(rng: random.Random, symbols: list[str]) -> dict[str, int]:
	assignments: dict[str, int] = {}
	for symbol in symbols:
		assignments[symbol] = sample_large_nonzero_integer(rng)
	return assignments


def format_assignment(name: str, value: int) -> str:
	return f"{name} = {value}"


def scalar_symbol_sign(scalar: Scalar) -> int:
	return -1 if scalar.value < 0 else 1


def evaluate_correctness(bundle: FormulaBundle, seed: int | None) -> tuple[list[str], list[str], list[str]]:
	rng = random.Random(None if seed is None else seed + 1_000_003)
	base_symbols = [
		scalar.name
		for affine_term in bundle.affine_terms
		for scalar in (affine_term.intercept, affine_term.slope)
	]
	inverse_symbol_names = {inverse_term.symbol.name for inverse_term in bundle.inverse_terms}
	base_symbols.extend(
		name
		for name in bundle.other_constants
		if name not in inverse_symbol_names
	)
	seen: set[str] = set()
	ordered_base_symbols: list[str] = []
	for symbol in base_symbols:
		if symbol not in seen:
			seen.add(symbol)
			ordered_base_symbols.append(symbol)

	base_assignments = sample_symbol_assignments(rng, ordered_base_symbols)
	x_value = sample_large_nonzero_integer(rng)
	assignments = dict(base_assignments)
	assignments["x"] = x_value

	derived_affine_values: list[str] = []
	for affine_term in bundle.affine_terms:
		alias_value = (
			scalar_symbol_sign(affine_term.intercept) * base_assignments[affine_term.intercept.name]
			+ scalar_symbol_sign(affine_term.slope) * base_assignments[affine_term.slope.name] * x_value
		)
		assignments[affine_term.name] = alias_value
		derived_affine_values.append(format_assignment(f"{affine_term.name}(x)", alias_value))

	for inverse_term in bundle.inverse_terms:
		source_value = base_assignments[inverse_term.source]
		assignments[inverse_term.symbol.name] = Fraction(1, source_value)

	assignment_lines = [format_assignment(symbol, base_assignments[symbol]) for symbol in ordered_base_symbols]
	assignment_lines.append(format_assignment("x", x_value))

	generated_lhs = evaluate_quadratic(bundle.lhs_quadratic, assignments, x_value)
	generated_rhs = evaluate_quadratic(bundle.rhs_quadratic, assignments, x_value)
	multilinear_lhs = evaluate_formal(bundle.lhs_formal, assignments)
	multilinear_rhs = evaluate_formal(bundle.rhs_formal, assignments)
	quadratic_value = evaluate_quadratic(
		add_quadratic(bundle.lhs_quadratic, scale_quadratic(bundle.rhs_quadratic, -1)),
		assignments,
		x_value,
	)
	generated_residual = generated_lhs - generated_rhs
	multilinear_residual = multilinear_lhs - multilinear_rhs
	consistent = generated_residual == multilinear_residual == quadratic_value

	check_lines = [
		f"Generated form: {generated_lhs} = {generated_rhs} -> residual {generated_residual}",
		f"Compact multilinear form: {multilinear_lhs} = {multilinear_rhs} -> residual {multilinear_residual}",
		f"Quadratic form: {quadratic_value} = 0 -> residual {quadratic_value}",
		f"Representation agreement: {'ok' if consistent else 'mismatch'}",
	]

	return assignment_lines, derived_affine_values, check_lines


class SymbolAllocator:
	def __init__(self, reserved: set[str] | None = None) -> None:
		self.reserved = set(reserved or set())
		self.index = 0

	def reserve(self, symbol: str) -> None:
		self.reserved.add(symbol)

	def next_symbol(self) -> str:
		while True:
			symbol = self._symbol_from_index(self.index)
			self.index += 1
			if symbol not in self.reserved:
				self.reserved.add(symbol)
				return symbol

	def _symbol_from_index(self, index: int) -> str:
		alphabet = [char for char in SYMBOL_ALPHABET if char != "x"]
		base = len(alphabet)
		value = index
		pieces: list[str] = []
		while True:
			pieces.append(alphabet[value % base])
			value = value // base - 1
			if value < 0:
				break
		return "".join(reversed(pieces))


def scalar_sign_prefix(scalar: Scalar) -> str:
	return "-" if scalar.value < 0 else ""


def constant_expr(scalar: Scalar) -> Expr:
	return Expr(
		f"{scalar_sign_prefix(scalar)}{scalar.name}",
		(0, 0, scalar.value),
		atom_formal(scalar.name, -1 if scalar.value < 0 else 1),
		(atom_formal(scalar.name, -1 if scalar.value < 0 else 1), {}, {}),
	)


def inverse_expr(display: str, symbol: Scalar) -> Expr:
	return Expr(
		f"inv({display})",
		(0, 0, symbol.value),
		atom_formal(symbol.name),
		(atom_formal(symbol.name), {}, {}),
	)


def format_term(prefix: str, body: str) -> str:
	if not prefix:
		return body
	return f"{prefix}{body}"


def linear_expr(intercept: Scalar, slope: Scalar) -> Expr:
	intercept_formal: FormalPolynomial = {}
	if intercept.value != 0:
		intercept_formal = atom_formal(intercept.name, -1 if intercept.value < 0 else 1)
	return Expr(
		f"({format_affine(intercept, slope)})",
		(0, slope.value, intercept.value),
		add_formal(
			intercept_formal,
			monomial_formal([slope.name, "x"], -1 if slope.value < 0 else 1),
		),
		(
			intercept_formal,
			atom_formal(slope.name, -1 if slope.value < 0 else 1),
			{},
		),
	)


def alias_expr(name: str, intercept: Scalar, slope: Scalar) -> Expr:
	intercept_formal = atom_formal(intercept.name, -1 if intercept.value < 0 else 1)
	slope_formal = atom_formal(slope.name, -1 if slope.value < 0 else 1)
	return Expr(
		f"{name}(x)",
		(0, slope.value, intercept.value),
		atom_formal(name),
		(intercept_formal, slope_formal, {}),
	)


def format_affine(intercept: Scalar, slope: Scalar) -> str:
	pieces: list[str] = []

	if intercept.value != 0:
		pieces.append(format_term(scalar_sign_prefix(intercept), intercept.name))

	slope_body = f"{slope.name}*x"
	if not pieces:
		pieces.append(format_term(scalar_sign_prefix(slope), slope_body))
	elif slope.value < 0:
		pieces.append(f"- {slope_body}")
	else:
		pieces.append(f"+ {slope_body}")

	if not pieces:
		return intercept.name
	return " ".join(pieces)


def add_expr(left: Expr, right: Expr) -> Expr:
	return Expr(
		f"({left.text} + {right.text})",
		add_coeffs(left.coeffs, right.coeffs),
		add_formal(left.formal, right.formal),
		add_quadratic(left.quadratic, right.quadratic),
	)


def sub_expr(left: Expr, right: Expr) -> Expr:
	return Expr(
		f"({left.text} - {right.text})",
		add_coeffs(left.coeffs, scale_coeffs(right.coeffs, -1)),
		add_formal(left.formal, scale_formal(right.formal, -1)),
		add_quadratic(left.quadratic, scale_quadratic(right.quadratic, -1)),
	)


def scale_expr(expr: Expr, factor: Scalar) -> Expr:
	factor_formal = atom_formal(factor.name, -1 if factor.value < 0 else 1)
	if factor.value < 0:
		return Expr(
			f"-{factor.name}*({expr.text})",
			scale_coeffs(expr.coeffs, factor.value),
			multiply_formal(factor_formal, expr.formal),
			(
				multiply_formal(factor_formal, expr.quadratic[0]),
				multiply_formal(factor_formal, expr.quadratic[1]),
				multiply_formal(factor_formal, expr.quadratic[2]),
			),
		)
	return Expr(
		f"{factor.name}*({expr.text})",
		scale_coeffs(expr.coeffs, factor.value),
		multiply_formal(factor_formal, expr.formal),
		(
			multiply_formal(factor_formal, expr.quadratic[0]),
			multiply_formal(factor_formal, expr.quadratic[1]),
			multiply_formal(factor_formal, expr.quadratic[2]),
		),
	)


def product_expr(left: Expr, right: Expr) -> Expr:
	return Expr(
		f"({left.text})*({right.text})",
		multiply_linear(left.coeffs, right.coeffs),
		multiply_formal(left.formal, right.formal),
		multiply_linear_quadratic(left.quadratic, right.quadratic),
	)


def square_expr(expr: Expr) -> Expr:
	return Expr(
		f"({expr.text})^2",
		multiply_linear(expr.coeffs, expr.coeffs),
		multiply_formal(expr.formal, expr.formal),
		multiply_linear_quadratic(expr.quadratic, expr.quadratic),
	)


def format_side(terms: list[Expr]) -> str:
	if not terms:
		return "z"

	pieces: list[str] = []
	for index, term in enumerate(terms):
		text = term.text.strip()
		if index == 0:
			pieces.append(text)
		elif text.startswith("-"):
			pieces.append(f"- {text[1:].lstrip()}")
		else:
			pieces.append(f"+ {text}")
	return " ".join(pieces)


def sum_formal(terms: list[Expr]) -> FormalPolynomial:
	formal: FormalPolynomial = {}
	for term in terms:
		formal = add_formal(formal, term.formal)
	return formal


def sample_integer(rng: random.Random) -> int:
	bit_length = 0
	while rng.random() < 0.5:
		bit_length += 1

	magnitude = rng.getrandbits(bit_length)
	if magnitude == 0:
		return 0
	return magnitude if rng.random() < 0.5 else -magnitude


def choose_unique_value(rng: random.Random, used: set[int], *, exclude_zero: bool = False) -> int:
	while True:
		value = sample_integer(rng)
		if exclude_zero and value == 0:
			continue
		if value not in used:
			used.add(value)
			return value


def choose_unique_scalar(
	rng: random.Random,
	used_numbers: set[int],
	allocator: SymbolAllocator,
	*,
	exclude_zero: bool = False,
) -> Scalar:
	return Scalar(
		name=allocator.next_symbol(),
		value=choose_unique_value(rng, used_numbers, exclude_zero=exclude_zero),
	)


def choose_formula_scalar(
	rng: random.Random,
	used_numbers: set[int],
	allocator: SymbolAllocator,
	pool: list[Scalar],
	*,
	exclude_zero: bool = False,
) -> Scalar:
	eligible = [scalar for scalar in pool if not exclude_zero or scalar.value != 0]
	if eligible and rng.random() < 0.65:
		return rng.choice(eligible)

	scalar = choose_unique_scalar(rng, used_numbers, allocator, exclude_zero=exclude_zero)
	pool.append(scalar)
	return scalar


def zero_scalar(allocator: SymbolAllocator) -> Scalar:
	return Scalar(name=allocator.next_symbol(), value=0)


def collect_scalar_names(*groups: list[Scalar]) -> list[str]:
	seen: set[str] = set()
	names: list[str] = []
	for group in groups:
		for scalar in group:
			if scalar.name not in seen:
				seen.add(scalar.name)
				names.append(scalar.name)
	return names


def make_inverse_name(source: str) -> str:
	cleaned = source.replace("(x)", "")
	cleaned = cleaned.replace("*", "_").replace("+", "_").replace("-", "_")
	cleaned = "".join(char for char in cleaned if char.isalnum() or char == "_")
	return f"inv_{cleaned}"


def chain_expr(parts: list[Expr], operators: list[str]) -> Expr:
	coeffs = parts[0].coeffs
	formal = dict(parts[0].formal)
	quadratic = parts[0].quadratic
	segments = [parts[0].text]
	for operator, part in zip(operators, parts[1:]):
		segments.append(f"{operator} {part.text}")
		if operator == "+":
			coeffs = add_coeffs(coeffs, part.coeffs)
			formal = add_formal(formal, part.formal)
			quadratic = add_quadratic(quadratic, part.quadratic)
		else:
			coeffs = add_coeffs(coeffs, scale_coeffs(part.coeffs, -1))
			formal = add_formal(formal, scale_formal(part.formal, -1))
			quadratic = add_quadratic(quadratic, scale_quadratic(part.quadratic, -1))
	return Expr(f"({' '.join(segments)})", coeffs, formal, quadratic)


def choose_linear_atom(
	rng: random.Random,
	linear_pool: list[Expr],
	used_numbers: set[int],
	allocator: SymbolAllocator,
	formula_scalars: list[Scalar],
	profile: ComplexityProfile,
) -> Expr:
	if rng.random() < profile.constant_atom_rate:
		return constant_expr(choose_formula_scalar(rng, used_numbers, allocator, formula_scalars))
	return rng.choice(linear_pool)


def build_linear_combo(
	rng: random.Random,
	linear_pool: list[Expr],
	used_numbers: set[int],
	allocator: SymbolAllocator,
	formula_scalars: list[Scalar],
	profile: ComplexityProfile,
	*,
	required: Expr | None = None,
	depth: int = 1,
) -> Expr:
	if depth > 0:
		part_count = rng.randint(*profile.linear_part_range)
	else:
		part_count = rng.randint(*profile.leaf_part_range)
	parts: list[Expr] = []
	if required is not None:
		parts.append(required)

	while len(parts) < part_count:
		if depth > 0 and rng.random() < profile.nested_linear_rate:
			nested = build_linear_combo(
				rng,
				linear_pool,
				used_numbers,
				allocator,
				formula_scalars,
				profile,
				depth=depth - 1,
			)
			if rng.random() < profile.nested_linear_scale_rate:
				nested = scale_expr(nested, choose_formula_scalar(rng, used_numbers, allocator, formula_scalars, exclude_zero=True))
			parts.append(nested)
		else:
			parts.append(choose_linear_atom(rng, linear_pool, used_numbers, allocator, formula_scalars, profile))

	rng.shuffle(parts)
	operators = [rng.choice(["+", "-"]) for _ in range(len(parts) - 1)]
	combo = chain_expr(parts, operators)
	if depth > 0 and rng.random() < profile.combo_scale_rate:
		combo = scale_expr(combo, choose_formula_scalar(rng, used_numbers, allocator, formula_scalars, exclude_zero=True))
	return combo


def build_quadratic_piece(
	rng: random.Random,
	alias_exprs: list[Expr],
	linear_pool: list[Expr],
	used_numbers: set[int],
	allocator: SymbolAllocator,
	formula_scalars: list[Scalar],
	profile: ComplexityProfile,
	direct_alias_product_rate: float,
	*,
	required: Expr | None = None,
	depth: int = 1,
) -> Expr:
	kind = rng.choice(["linear", "product", "square"])
	if kind == "product" and (required is not None or rng.random() < direct_alias_product_rate):
		left = required if required is not None and rng.random() < 0.7 else rng.choice(alias_exprs)
		right_choices = [alias for alias in alias_exprs if alias is not left]
		right = rng.choice(right_choices or alias_exprs)
		piece = product_expr(left, right)
	else:
		left = build_linear_combo(
			rng,
			linear_pool,
			used_numbers,
			allocator,
			formula_scalars,
			profile,
			required=required,
			depth=max(depth, 0),
		)
		if kind == "linear":
			piece = left
		elif kind == "square":
			piece = square_expr(left)
		else:
			right_required = rng.choice(alias_exprs) if rng.random() < 0.4 else None
			right = build_linear_combo(
				rng,
				linear_pool,
				used_numbers,
				allocator,
				formula_scalars,
				profile,
				required=right_required,
				depth=max(depth - 1, 0),
			)
			piece = product_expr(left, right)

	if depth > 0 and rng.random() < profile.compound_piece_rate:
		part_count = rng.randint(*profile.compound_piece_range)
		parts = [piece]
		while len(parts) < part_count:
			variant_kind = rng.choice(["linear", "product", "square"])
			variant_left = build_linear_combo(
				rng,
				linear_pool,
				used_numbers,
				allocator,
				formula_scalars,
				profile,
				depth=max(depth - 1, 0),
			)
			if variant_kind == "linear":
				parts.append(variant_left)
			elif variant_kind == "square":
				parts.append(square_expr(variant_left))
			else:
				variant_right = build_linear_combo(
					rng,
					linear_pool,
					used_numbers,
					allocator,
					formula_scalars,
					profile,
					depth=max(depth - 1, 0),
				)
				parts.append(product_expr(variant_left, variant_right))
		operators = [rng.choice(["+", "-"]) for _ in range(len(parts) - 1)]
		piece = chain_expr(parts, operators)

	return scale_expr(piece, choose_formula_scalar(rng, used_numbers, allocator, formula_scalars, exclude_zero=True))


def build_alias_term(
	rng: random.Random,
	alias_exprs: list[Expr],
	linear_pool: list[Expr],
	current_alias: Expr,
	used_numbers: set[int],
	allocator: SymbolAllocator,
	formula_scalars: list[Scalar],
	profile: ComplexityProfile,
	direct_alias_product_rate: float,
) -> Expr:
	return build_quadratic_piece(
		rng,
		alias_exprs,
		linear_pool,
		used_numbers,
		allocator,
		formula_scalars,
		profile,
		direct_alias_product_rate,
		required=current_alias,
		depth=profile.quadratic_depth,
	)


def build_extra_term(
	rng: random.Random,
	alias_exprs: list[Expr],
	linear_pool: list[Expr],
	used_numbers: set[int],
	allocator: SymbolAllocator,
	formula_scalars: list[Scalar],
	profile: ComplexityProfile,
	direct_alias_product_rate: float,
) -> Expr:
	if rng.random() < profile.extra_constant_rate:
		return constant_expr(choose_formula_scalar(rng, used_numbers, allocator, formula_scalars))
	return build_quadratic_piece(
		rng,
		alias_exprs,
		linear_pool,
		used_numbers,
		allocator,
		formula_scalars,
		profile,
		direct_alias_product_rate,
		depth=profile.quadratic_depth,
	)


def generate_formula(
	seed: int | None = None,
	alias_count: int = 2,
	extra_terms: int = 4,
	complexity: str = "medium",
	direct_alias_product_rate: float = 0.35,
	inverse_rate: float = 0.5,
) -> FormulaBundle:
	rng = random.Random(seed)
	alias_count = max(1, alias_count)
	extra_terms = max(0, extra_terms)
	profile = COMPLEXITY_PRESETS.get(complexity, COMPLEXITY_PRESETS["medium"])
	direct_alias_product_rate = min(max(direct_alias_product_rate, 0.0), 1.0)
	inverse_rate = min(max(inverse_rate, 0.0), 1.0)
	used_numbers: set[int] = set()
	symbol_allocator = SymbolAllocator(set(FUNCTION_NAMES))
	formula_scalars: list[Scalar] = []
	other_scalars: list[Scalar] = []

	alias_pool: list[Expr] = []
	linear_pool: list[Expr] = []
	affine_terms: list[AffineTerm] = []
	function_names = list(FUNCTION_NAMES)

	for index in range(1, alias_count + 1):
		intercept = choose_unique_scalar(rng, used_numbers, symbol_allocator, exclude_zero=True)
		slope = choose_unique_scalar(rng, used_numbers, symbol_allocator, exclude_zero=True)
		if index <= len(function_names):
			name = function_names[index - 1]
		else:
			name = f"{function_names[0]}{symbol_allocator.next_symbol()}"
		affine_terms.append(AffineTerm(name, intercept, slope))
		alias_instance = alias_expr(name, intercept, slope)
		alias_pool.append(alias_instance)
		linear_pool.append(alias_instance)

	raw_linear_count = rng.randint(1, 3)
	for _ in range(raw_linear_count):
		intercept = choose_unique_scalar(rng, used_numbers, symbol_allocator)
		slope = choose_unique_scalar(rng, used_numbers, symbol_allocator, exclude_zero=True)
		other_scalars.extend([intercept, slope])
		linear_pool.append(linear_expr(intercept, slope))

	inverse_candidates: list[str] = []
	for scalar in other_scalars + formula_scalars:
		if scalar.value != 0:
			inverse_candidates.append(scalar.name)

	inverse_terms: list[InverseTerm] = []
	for source_text in inverse_candidates:
		if rng.random() > inverse_rate:
			continue
		inverse_symbol = choose_unique_scalar(rng, used_numbers, symbol_allocator)
		inverse_term = inverse_expr(source_text, inverse_symbol)
		inverse_terms.append(InverseTerm(source=source_text, display=inverse_term.text, symbol=inverse_symbol))
		linear_pool.extend([inverse_term, inverse_term])

	if not inverse_terms and inverse_candidates:
		source_text = inverse_candidates[0]
		inverse_symbol = choose_unique_scalar(rng, used_numbers, symbol_allocator)
		inverse_term = inverse_expr(source_text, inverse_symbol)
		inverse_terms.append(InverseTerm(source=source_text, display=inverse_term.text, symbol=inverse_symbol))
		linear_pool.extend([inverse_term, inverse_term])

	quadratic_scale = choose_formula_scalar(rng, used_numbers, symbol_allocator, formula_scalars, exclude_zero=True)
	first_alias = alias_pool[0]
	second_factor = build_linear_combo(
		rng,
		linear_pool,
		used_numbers,
		symbol_allocator,
		formula_scalars,
		profile,
		required=rng.choice(alias_pool) if len(alias_pool) > 1 else None,
		depth=profile.core_depth,
	)
	if rng.random() < 0.5:
		core = scale_expr(product_expr(first_alias, second_factor), quadratic_scale)
	else:
		core = scale_expr(square_expr(build_linear_combo(
			rng,
			linear_pool,
			used_numbers,
			symbol_allocator,
			formula_scalars,
			profile,
			required=first_alias,
			depth=profile.core_depth,
		)), quadratic_scale)

	terms = [core]
	for alias_instance in alias_pool[1:]:
		terms.append(build_alias_term(
			rng,
			alias_pool,
			linear_pool,
			alias_instance,
			used_numbers,
			symbol_allocator,
			formula_scalars,
			profile,
			direct_alias_product_rate,
		))

	for _ in range(extra_terms):
		terms.append(build_extra_term(
			rng,
			alias_pool,
			linear_pool,
			used_numbers,
			symbol_allocator,
			formula_scalars,
			profile,
			direct_alias_product_rate,
		))

	total = (0, 0, 0)
	lhs_terms: list[Expr] = []
	rhs_terms: list[Expr] = []

	for index, term in enumerate(terms):
		if index == 0 or rng.random() < 0.5:
			lhs_terms.append(term)
			total = add_coeffs(total, term.coeffs)
		else:
			rhs_terms.append(term)
			total = add_coeffs(total, scale_coeffs(term.coeffs, -1))

	if not lhs_terms:
		lhs_terms.append(terms[0])
	if not rhs_terms:
		fallback_zero = zero_scalar(symbol_allocator)
		other_scalars.append(fallback_zero)
		rhs_terms.append(constant_expr(fallback_zero))

	equation = f"{format_side(lhs_terms)} = {format_side(rhs_terms)}"
	lhs_formal = sum_formal(lhs_terms)
	rhs_formal = sum_formal(rhs_terms)
	lhs_quadratic = sum_quadratic(lhs_terms)
	rhs_quadratic = sum_quadratic(rhs_terms)
	multilinear_equation = f"{format_formal_polynomial(lhs_formal)} = {format_formal_polynomial(rhs_formal)}"
	quadratic_form = format_quadratic_form(add_quadratic(lhs_quadratic, scale_quadratic(rhs_quadratic, -1)))
	other_constants = collect_scalar_names(
		other_scalars,
		formula_scalars,
		[inverse_term.symbol for inverse_term in inverse_terms],
	)
	return FormulaBundle(
		affine_terms=affine_terms,
		inverse_terms=inverse_terms,
		other_constants=other_constants,
		equation=equation,
		multilinear_equation=multilinear_equation,
		quadratic_form=quadratic_form,
		coeffs=total,
		lhs_formal=lhs_formal,
		rhs_formal=rhs_formal,
		lhs_quadratic=lhs_quadratic,
		rhs_quadratic=rhs_quadratic,
	)


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate disguised quadratic equations with affine u(x) terms.")
	parser.add_argument("--seed", type=int, default=None, help="Seed for reproducible output.")
	parser.add_argument("--aliases", type=int, default=2, help="How many u_i(x) aliases to define.")
	parser.add_argument("--extras", type=int, default=4, help="How many extra terms to add on top of the quadratic core.")
	parser.add_argument(
		"--complexity",
		choices=sorted(COMPLEXITY_PRESETS),
		default="medium",
		help="Overall structural complexity profile for length, nesting, and density.",
	)
	parser.add_argument(
		"--direct-alias-product-rate",
		type=float,
		default=0.35,
		help="Probability that a product term uses raw affine aliases directly.",
	)
	parser.add_argument(
		"--inverse-rate",
		type=float,
		default=0.5,
		help="Probability that a candidate source gets wrapped in inv(...).",
	)
	args = parser.parse_args()

	bundle = generate_formula(
		seed=args.seed,
		alias_count=args.aliases,
		extra_terms=args.extras,
		complexity=args.complexity,
		direct_alias_product_rate=args.direct_alias_product_rate,
		inverse_rate=args.inverse_rate,
	)
	assignment_lines, derived_affine_values, check_lines = evaluate_correctness(bundle, args.seed)

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