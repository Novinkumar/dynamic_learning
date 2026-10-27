"""A local, validated generator for fresh Python practice questions.

This is deliberately not described as a large language model. It combines a
curated bank with parameterized code-tracing templates, then validates options,
answers, explanations, and uniqueness. It is the always-available fallback for
the AI practice studio and keeps the project usable without an API key.
"""

from __future__ import annotations

import math
import operator
import random
import re

from .catalog import QUIZ_QUESTIONS


TIERS = ("foundation", "core", "stretch")
TOPIC_ALIASES = {name.lower(): name for name in QUIZ_QUESTIONS}

DEFAULT_SKILLS = {
    "Variables": ["Assignment", "Naming", "Rebinding", "Expressions"],
    "Data Types": ["Types", "Conversions", "Operators", "Booleans"],
    "Conditionals": ["Comparisons", "Branching", "Boolean logic", "Membership"],
    "Loops": ["Range", "Iteration", "Break/continue", "Accumulators"],
    "Functions": ["Return values", "Parameters", "Scope", "Defaults"],
    "Lists": ["Indexing", "Slicing", "List methods", "Comprehensions"],
    "Basic Algorithms": ["Linear search", "Accumulators", "Complexity", "Recursion"],
}

TIER_WEIGHTS = {
    "foundation": (0.65, 0.30, 0.05),
    "core": (0.25, 0.50, 0.25),
    "stretch": (0.05, 0.35, 0.60),
    "adaptive": (0.25, 0.50, 0.25),
}


def _clean(value, limit=500):
    """Collapse model- or template-generated whitespace into safe text."""
    return " ".join(str(value).split())[:limit]


def _prompt_key(value):
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _numeric_distractors(result, candidates, rng, count=3):
    """Return distinct string distractors, excluding the correct value."""
    result_text = str(result)
    seen = {result_text}
    values = []
    for candidate in candidates:
        candidate = candidate() if callable(candidate) else candidate
        text = str(candidate)
        if text not in seen:
            seen.add(text)
            values.append(text)
    rng.shuffle(values)
    offset = 1
    while len(values) < count:
        # `result` may be an int, a float, or a preformatted float string.
        try:
            numeric = float(result)
            text = str(int(numeric + offset)) if isinstance(result, int) else f"{numeric + offset / 2:.2f}"
        except (TypeError, ValueError):
            text = f"another value {offset}"
        if text not in seen:
            seen.add(text)
            values.append(text)
        offset += 1
    return values[:count]


def _q(prompt, correct, distractors, explanation, skill, tier="core", topic=""):
    """Create a consistent question dictionary and guarantee four options."""
    options = [_clean(correct, 180)]
    seen = {options[0]}
    for item in distractors:
        text = _clean(item, 180)
        if text and text not in seen:
            seen.add(text)
            options.append(text)
    for fallback in ("None of these", "It depends on the operating system", "An error occurs", "Cannot be determined"):
        if len(options) >= 4:
            break
        if fallback not in seen:
            seen.add(fallback)
            options.append(fallback)
    return {
        "prompt": prompt,
        "options": options[:4],
        "answer": options[0],
        "explanation": explanation,
        "skill": skill,
        "difficulty": tier,
        "topic": topic,
        "source": "offline_generator",
    }


def _normalise(question, rng, topic):
    prompt = _clean(question.get("prompt"), 600)
    answer = _clean(question.get("answer"), 180)
    options = []
    seen = set()
    for option in [answer, *question.get("options", [])]:
        text = _clean(option, 180)
        if text and text not in seen:
            seen.add(text)
            options.append(text)
    for fallback in ("None of these", "An error occurs", "Cannot be determined", "It is undefined"):
        if len(options) >= 4:
            break
        if fallback not in seen:
            seen.add(fallback)
            options.append(fallback)
    if not prompt or not answer or len(options) < 4:
        raise ValueError("Invalid question template")
    rng.shuffle(options)
    return {
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": _clean(question.get("explanation") or f"The correct answer is {answer}.", 600),
        "skill": _clean(question.get("skill") or "Python foundations", 80),
        "difficulty": question.get("difficulty", "core") if question.get("difficulty") in TIERS else "core",
        "topic": topic,
        "source": question.get("source", "offline_generator"),
    }


def curated_bank(topic):
    """Return seeded questions with skill and tier metadata for AI sampling."""
    questions = QUIZ_QUESTIONS.get(topic, [])
    skills = DEFAULT_SKILLS.get(topic, ["Python foundations"])
    bank = []
    for index, (prompt, options, answer, explanation) in enumerate(questions):
        bank.append({
            "prompt": prompt,
            "options": list(options),
            "answer": answer,
            "explanation": explanation,
            "skill": skills[index % len(skills)],
            "difficulty": TIERS[min(index // 2, 2)],
            "topic": topic,
            "source": "curated_bank",
        })
    return bank


# ---------------------------------------------------------------------------
# Parameterized code-tracing templates. Each function returns one fresh item.
# ---------------------------------------------------------------------------

def _variables_reassignment(rng, tier):
    a = rng.randint(3, 35)
    b = rng.randint(2, 16)
    op = rng.choice(["+", "+", "-"] if tier == "foundation" else ["+", "-", "*"] if tier == "core" else ["-", "*", "*"])
    operation = {"+": operator.add, "-": operator.sub, "*": operator.mul}[op]
    result = operation(a, b)
    op_token = f"{op}="
    prompt = f"What is printed?\nx = {a}\nx {op_token} {b}\nprint(x)"
    distractors = _numeric_distractors(result, [a, b, a + b, a - b, a * b, a // max(b, 1)], rng)
    return _q(prompt, str(result), distractors,
              f"Augmented assignment updates x using the old value: {a} {op} {b} = {result}.",
              "Assignment tracing", tier, "Variables")


def _variables_swap(rng, tier):
    a, b = rng.sample(range(2, 40), 2)
    if tier == "stretch":
        c = rng.randint(2, 40)
        prompt = f"What is printed?\na, b, c = {a}, {b}, {c}\na, b, c = c, a, b\nprint(a, b, c)"
        correct = f"{c} {a} {b}"
        distractors = [f"{a} {b} {c}", f"{b} {c} {a}", f"{c} {b} {a}"]
        explanation = "Tuple assignment evaluates the right side first, then binds the values in order."
    else:
        prompt = f"What is printed?\na, b = {a}, {b}\na, b = b, a\nprint(a, b)"
        correct = f"{b} {a}"
        distractors = [f"{a} {b}", f"{a} {a}", f"{b} {b}"]
        explanation = "The right-hand values are read before either variable is reassigned, so the values swap."
    return _q(prompt, correct, distractors, explanation, "Multiple assignment", tier, "Variables")


def _variables_names(rng, tier):
    choices = [
        ("number of quiz attempts", "attempt_count"),
        ("learner's average score", "average_score"),
        ("current level", "current_level"),
        ("items in a cart", "cart_items"),
        ("remaining time in seconds", "seconds_left"),
    ]
    context, valid = rng.choice(choices)
    invalid = rng.sample(["2score", "class", "total-score", "total score", "import", "first.value"], 3)
    prompt = f"Which name is valid and readable for a variable storing the {context}?"
    return _q(prompt, valid, invalid,
              "Python names may use letters, digits, and underscores, cannot start with a digit, and cannot be keywords.",
              "Naming", tier, "Variables")


def _variables_expression(rng, tier):
    a, b, c = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 9)
    if tier == "stretch":
        prompt = f"What is printed?\na = {a}\nb = {b}\nprint(a ** 2 + b)"
        result = a ** 2 + b
        distractors = _numeric_distractors(result, [a * 2 + b, a * a, a + b, a * b], rng)
        explanation = "Exponentiation is evaluated before addition, so a squared is added to b."
    else:
        prompt = f"What is printed?\na = {a}\nb = {b}\nprint(a * {c} + b)"
        result = a * c + b
        distractors = _numeric_distractors(result, [a * (c + b), a * c - b, a + b + c, a * c], rng)
        explanation = "Multiplication is evaluated before addition; stored values a and b are then combined."
    return _q(prompt, str(result), distractors, explanation, "Expressions", tier, "Variables")


def _variables_string_length(rng, tier):
    words = ["Python", "learner", "adaptive", "quiz", "mastery", "practice", "function", "list"]
    word = rng.choice(words)
    padding = "  " + word + " " if tier == "stretch" else word
    expression = 'name.strip()' if tier == "stretch" else 'name'
    prompt = f'What is printed?\nname = "{padding}"\nprint(len({expression}))'
    result = len(word)
    distractors = _numeric_distractors(result, [result - 1, result + 1, result * 2, result + 3], rng)
    explanation = f"len() counts the characters in {'the stripped string' if tier == 'stretch' else 'name'}, which has {result}."
    return _q(prompt, str(result), distractors, explanation, "Strings", tier, "Variables")


def _variables_unpacking(rng, tier):
    a, b, c = rng.sample(range(3, 30), 3)
    if tier == "stretch":
        prompt = f"What is printed?\na, b, c = {a}, {b}, {c}\na, b = b, a + b\nprint(a + c)"
        result = b + c
        distractors = _numeric_distractors(result, [a + c, a + b, a + b + c], rng)
        explanation = "After the second assignment, a holds the old b; adding c gives the printed value."
    else:
        prompt = f"What is printed?\na, b, c = {a}, {b}, {c}\nprint(b + c)"
        result = b + c
        distractors = _numeric_distractors(result, [a + b, a + c, a + b + c], rng)
        explanation = "The values are unpacked in order, so b and c keep their assigned numeric values."
    return _q(prompt, str(result), distractors, explanation, "Multiple assignment", tier, "Variables")


def _types_literal(rng, tier):
    literals = [
        ("7", "int"), ("3.14", "float"), ("'hello'", "str"), ("True", "bool"),
        ("[1, 2]", "list"), ("(1, 2)", "tuple"), ("{'a': 1}", "dict"), ("None", "NoneType"),
    ]
    literal, correct = rng.choice(literals)
    all_types = ["int", "float", "str", "bool", "list", "tuple", "dict", "NoneType"]
    distractors = rng.sample([item for item in all_types if item != correct], 3)
    prompt = f"What is the name of the type of {literal} in Python?"
    return _q(prompt, correct, distractors,
              f"The literal {literal} is an instance of {correct}.", "Types", tier, "Data Types")


def _types_conversion(rng, tier):
    n = rng.randint(4, 49)
    m = rng.randint(2, 19)
    result = n + m
    prompt = f'What is printed?\nprint(int("{n}") + {m})'
    distractors = [f"{n}{m}", str(n * m), str(n - m), str(n)]
    return _q(prompt, str(result), distractors,
              f'int converts the string "{n}" to a number before addition.', "Conversions", tier, "Data Types")


def _types_operator(rng, tier):
    op = rng.choice(["//", "%"] if tier == "foundation" else ["//", "%", "**"] if tier == "core" else ["//", "%", "**", "/"])
    if op == "**":
        a, b = rng.randint(2, 9), rng.randint(2, 3)
        result = a ** b
    elif op == "/":
        b = rng.choice([2, 4, 5])
        a = b * rng.randint(2, 9)
        result = repr(a / b)
    else:
        a, b = rng.randint(8, 40), rng.randint(2, 9)
        result = a // b if op == "//" else a % b
    prompt = f"What is printed?\nprint({a} {op} {b})"
    distractors = _numeric_distractors(result, [a, b, a + b, a - b, a * b], rng)
    explanation = {"//": "Floor division returns the whole-number quotient.",
                   "%": "The modulo operator returns the remainder.",
                   "**": "Exponentiation raises the left value to the right-hand power.",
                   "/": "True division always returns a float, even when the result is whole."}[op]
    return _q(prompt, str(result), distractors, explanation, "Operators", tier, "Data Types")


def _types_boolean(rng, tier):
    values = [("0", "False"), ("1", "True"), ("''", "False"), ("'Python'", "True"), ("[]", "False"), ("[0]", "True")]
    literal, correct = rng.choice(values)
    prompt = f"What is printed?\nprint(bool({literal}))"
    distractors = ["True" if correct == "False" else "False", "None", "0", "An error occurs"]
    return _q(prompt, correct, distractors,
              f"bool({literal}) is {correct} because of Python's truth-value rules.", "Booleans", tier, "Data Types")


def _types_concatenation(rng, tier):
    a, b = rng.randint(10, 99), rng.randint(10, 99)
    correct = f"{a}{b}"
    prompt = f"What is printed?\nprint(str({a}) + str({b}))"
    distractors = [str(a + b), str(a * b), str(a - b), str(b)]
    return _q(prompt, correct, distractors,
              "Converting both numbers to strings makes + concatenate their text instead of adding them.",
              "Strings", tier, "Data Types")


def _types_rounding(rng, tier):
    base = rng.randint(1, 12)
    decimal = rng.choice([0.24, 0.26, 0.37, 0.63, 0.74, 0.89])
    value = base + decimal
    result = round(value, 1)
    prompt = f"What is printed?\nprint(round({value:.2f}, 1))"
    distractors = [f"{base}.0", f"{base + 1}.0", f"{round(value, 0):.1f}", str(int(value))]
    return _q(prompt, f"{result:.1f}", distractors,
              "round(value, 1) keeps one digit after the decimal point.", "Numbers", tier, "Data Types")


def _condition_comparison(rng, tier):
    x = rng.randint(1, 30)
    threshold = rng.randint(1, 30)
    op = rng.choice([">", "<", ">=", "<=", "==", "!="])
    operations = {">": operator.gt, "<": operator.lt, ">=": operator.ge,
                  "<=": operator.le, "==": operator.eq, "!=": operator.ne}
    truth = operations[op](x, threshold)
    correct = "yes" if truth else "no"
    prompt = (f"What is printed?\nx = {x}\nif x {op} {threshold}:\n"
              '    print("yes")\nelse:\n    print("no")')
    return _q(prompt, correct, ["yes" if correct == "no" else "no", "yes then no", "nothing"],
              f"The condition {x} {op} {threshold} is {truth}, so only one branch runs.",
              "Comparisons", tier, "Conditionals")


def _condition_boolean_ops(rng, tier):
    a, b = rng.choice([True, False]), rng.choice([True, False])
    op = rng.choice(["and", "or"])
    result = (a and b) if op == "and" else (a or b)
    prompt = f"What is printed?\nprint({a} {op} {b})"
    return _q(prompt, str(result), [str(not result), "None", "An error occurs"],
              f"{op} evaluates the two Boolean values and produces {result}.",
              "Boolean logic", tier, "Conditionals")


def _condition_elif(rng, tier):
    score = rng.randint(45, 100)
    if score >= 90:
        correct = "A"
    elif score >= 70:
        correct = "B"
    else:
        correct = "C"
    prompt = (f"What is printed?\nscore = {score}\nif score >= 90:\n"
              '    print("A")\nelif score >= 70:\n    print("B")\nelse:\n    print("C")')
    return _q(prompt, correct, [item for item in ("A", "B", "C") if item != correct][:3] + ["A then B"],
              "Python stops at the first true branch in an if/elif/else chain.",
              "Branching", tier, "Conditionals")


def _condition_ternary(rng, tier):
    age = rng.randint(10, 40)
    correct = "adult" if age >= 18 else "minor"
    prompt = (f"What is printed?\nage = {age}\n"
              'status = "adult" if age >= 18 else "minor"\nprint(status)')
    return _q(prompt, correct, ["adult" if correct == "minor" else "minor", "True", "None"],
              "A conditional expression chooses one value based on the comparison.",
              "Conditional expressions", tier, "Conditionals")


def _condition_membership(rng, tier):
    word = rng.choice(["python", "function", "mastery", "adaptive", "conditional"])
    letter = rng.choice("aeioupythnfr")
    result = letter in word
    prompt = f'What is printed?\nprint("{letter}" in "{word}")'
    return _q(prompt, str(result), [str(not result), "None", "An error occurs"],
              f"The letter {letter!r} {'is' if result else 'is not'} present in {word!r}.",
              "Membership", tier, "Conditionals")


def _condition_chained(rng, tier):
    x = rng.randint(1, 40)
    low, high = rng.randint(1, 15), rng.randint(20, 45)
    result = low < x < high
    correct = "inside" if result else "outside"
    prompt = (f"What is printed?\nx = {x}\nif {low} < x < {high}:\n"
              '    print("inside")\nelse:\n    print("outside")')
    return _q(prompt, correct, ["inside" if correct == "outside" else "outside", "inside then outside", "nothing"],
              f"A chained comparison is equivalent to {low} < x and x < {high}; here it is {result}.",
              "Chained comparisons", tier, "Conditionals")


def _loop_range_sum(rng, tier):
    start = rng.randint(0, 5)
    stop = start + rng.randint(3, 12 if tier != "stretch" else 18)
    result = sum(range(start, stop))
    prompt = (f"What is printed?\ntotal = 0\nfor n in range({start}, {stop}):\n"
              "    total += n\nprint(total)")
    distractors = _numeric_distractors(result, [stop - start, sum(range(start, stop + 1)), stop, start + stop], rng)
    return _q(prompt, str(result), distractors,
              "range excludes the stop value, and the loop adds each remaining number to total.",
              "Accumulators", tier, "Loops")


def _loop_range_count(rng, tier):
    start = rng.randint(0, 8)
    step = rng.randint(2, 5)
    stop = start + step * rng.randint(3, 8) + 1
    values = list(range(start, stop, step))
    prompt = (f"How many times does this loop run?\nfor i in range({start}, {stop}, {step}):\n"
              "    print(i)")
    result = len(values)
    distractors = _numeric_distractors(result, [stop - start, step, values[-1] if values else 0, stop], rng)
    return _q(prompt, str(result), distractors,
              f"range({start}, {stop}, {step}) produces {result} values before reaching the stop value.",
              "Range", tier, "Loops")


def _loop_while(rng, tier):
    start = rng.randint(0, 8)
    step = rng.randint(1, 4)
    limit = start + rng.randint(4, 15)
    value = start
    while value < limit:
        value += step
    prompt = (f"What is printed?\nn = {start}\nwhile n < {limit}:\n"
              f"    n += {step}\nprint(n)")
    distractors = _numeric_distractors(value, [start, limit, limit + step, start + step], rng)
    return _q(prompt, str(value), distractors,
              "The loop continues until n is no longer below the limit, then prints the final value.",
              "While loops", tier, "Loops")


def _loop_break(rng, tier):
    n = rng.randint(4, 12)
    break_at = rng.randint(1, n - 1)
    prompt = (f"What is printed?\nfor i in range({n}):\n"
              f"    if i == {break_at}:\n        break\nprint(i)")
    distractors = _numeric_distractors(break_at, [n - 1, 0, n, break_at + 1], rng)
    return _q(prompt, str(break_at), distractors,
              "break exits the loop immediately, so i keeps the value from the final iteration.",
              "Break", tier, "Loops")


def _loop_continue(rng, tier):
    n = rng.randint(5, 12)
    result = sum(i for i in range(n) if i % 2)
    prompt = (f"What is printed?\ntotal = 0\nfor i in range({n}):\n"
              "    if i % 2 == 0:\n        continue\n    total += i\nprint(total)")
    distractors = _numeric_distractors(result, [sum(range(n)), sum(i for i in range(n) if i % 2 == 0), n], rng)
    return _q(prompt, str(result), distractors,
              "continue skips the rest of an even-numbered iteration, so only odd values are added.",
              "Continue", tier, "Loops")


def _loop_factorial(rng, tier):
    k = rng.randint(3, 8)
    result = math.factorial(k - 1)
    prompt = (f"What is printed?\ntotal = 1\nfor n in range(1, {k}):\n"
              "    total *= n\nprint(total)")
    distractors = _numeric_distractors(result, [k, sum(range(1, k)), 2 ** (k - 1)], rng)
    return _q(prompt, str(result), distractors,
              "The loop multiplies every integer from 1 up to, but not including, the stop value.",
              "Accumulators", tier, "Loops")


def _function_return(rng, tier):
    a, m, c = rng.randint(2, 12), rng.randint(2, 7), rng.randint(1, 9)
    result = a * m + c
    if tier == "stretch":
        result = result * m + c
        prompt = (f"What is printed?\ndef compute(x):\n    return x * {m} + {c}\n"
                  f"print(compute(compute({a})))")
        explanation = "The inner call returns a value that becomes the argument of the outer call."
        distractors = _numeric_distractors(result, [a * m + c, a * m, a * m * 2 + c], rng)
    else:
        prompt = (f"What is printed?\ndef compute(x):\n    return x * {m} + {c}\n"
                  f"print(compute({a}))")
        explanation = "The argument is bound to x; return sends the computed value back to print."
        distractors = _numeric_distractors(result, [a * m, a + c, a * m - c], rng)
    return _q(prompt, str(result), distractors, explanation, "Return values", tier, "Functions")


def _function_default(rng, tier):
    default = rng.choice(["Ada", "Learner", "Sam", "Guest"])
    override = rng.choice(["Maya", "Ravi", "Lina", "Noah"])
    call = f'greet("{override}")' if tier != "foundation" else "greet()"
    correct = "Hi " + (override if tier != "foundation" else default)
    prompt = (f"What is printed?\ndef greet(name=\"{default}\"):\n"
              f'    return "Hi " + name\nprint({call})')
    return _q(prompt, correct, [f"Hi {override if tier == 'foundation' else default}", "Hi name", "None"],
              "A default parameter is used only when the caller supplies no value.",
              "Default parameters", tier, "Functions")


def _function_keyword(rng, tier):
    w, h = rng.randint(2, 12), rng.randint(2, 12)
    result = w * h
    prompt = (f"What is printed?\ndef area(width, height):\n    return width * height\n"
              f"print(area(height={h}, width={w}))")
    distractors = _numeric_distractors(result, [w + h, w - h, h * h], rng)
    return _q(prompt, str(result), distractors,
              "Keyword arguments match names rather than position, so width receives w and height receives h.",
              "Keyword arguments", tier, "Functions")


def _function_lambda(rng, tier):
    a, m, c = rng.randint(2, 12), rng.randint(2, 7), rng.randint(1, 9)
    result = a * m - c
    prompt = f"What is printed?\nf = lambda x: x * {m} - {c}\nprint(f({a}))"
    distractors = _numeric_distractors(result, [a * m, a + m - c, a * (m - c)], rng)
    return _q(prompt, str(result), distractors,
              "A lambda creates a small anonymous function; calling it substitutes the argument for x.",
              "Lambda functions", tier, "Functions")


def _function_scope(rng, tier):
    a, b = rng.sample(range(3, 30), 2)
    prompt = (f"What is printed?\nvalue = {a}\ndef change(x):\n"
              f"    x = {b}\n    return x\nchange(value)\nprint(value)")
    distractors = _numeric_distractors(a, [b, a + b, a - b], rng)
    return _q(prompt, str(a), distractors,
              "Assigning to the local parameter x does not rebind the outer value variable.",
              "Scope", tier, "Functions")


def _function_print_return(rng, tier):
    a = rng.randint(2, 30)
    prompt = (f"What is printed on the two lines?\ndef show(x):\n    print(x)\n"
              f"print(show({a}))")
    correct = f"{a} then None"
    distractors = [f"None then {a}", str(a), "None"]
    return _q(prompt, correct, distractors,
              "show prints its argument but has no return statement, so the caller receives and prints None.",
              "Print vs return", tier, "Functions")


def _list_index(rng, tier):
    values = rng.sample(range(2, 40), rng.randint(4, 6))
    index = rng.randrange(len(values))
    result = values[index]
    prompt = f"What is printed?\nitems = {values!r}\nprint(items[{index}])"
    distractors = _numeric_distractors(result, [values[0], values[-1], sum(values), len(values)], rng)
    return _q(prompt, str(result), distractors,
              "Python indexes lists from zero, so the selected position returns its stored value.",
              "Indexing", tier, "Lists")


def _list_slice(rng, tier):
    values = rng.sample(range(2, 40), rng.randint(5, 7))
    start = rng.randint(0, len(values) - 3)
    end = rng.randint(start + 1, len(values))
    result = repr(values[start:end])
    prompt = f"What is printed?\nitems = {values!r}\nprint(items[{start}:{end}])"
    distractors = [repr(values[start:end + 1]), repr(values[start + 1:end]), repr(values[:end]), repr(values[start:])]
    return _q(prompt, result, distractors,
              "A slice includes the start index and excludes the end index.", "Slicing", tier, "Lists")


def _list_append(rng, tier):
    values = rng.sample(range(2, 30), rng.randint(3, 7))
    extra = rng.randint(2, 30)
    result = len(values) + 1
    prompt = f"What is printed?\nitems = {values!r}\nitems.append({extra})\nprint(len(items))"
    distractors = _numeric_distractors(result, [len(values), len(values) + extra, len(values) * 2], rng)
    return _q(prompt, str(result), distractors,
              "append adds one item to the end, increasing the list length by one.",
              "List methods", tier, "Lists")


def _list_sum(rng, tier):
    values = rng.sample(range(2, 25), rng.randint(4, 7))
    result = sum(values)
    prompt = f"What is printed?\nitems = {values!r}\nprint(sum(items))"
    distractors = _numeric_distractors(result, [max(values), min(values), len(values)], rng)
    return _q(prompt, str(result), distractors,
              "sum adds all numeric values in the list.", "Aggregation", tier, "Lists")


def _list_comprehension(rng, tier):
    start = rng.randint(0, 4)
    stop = start + rng.randint(3, 7)
    m = rng.randint(2, 5)
    result = repr([x * m for x in range(start, stop)])
    prompt = f"What is printed?\nprint([x * {m} for x in range({start}, {stop})])"
    distractors = [repr([x + m for x in range(start, stop)]),
                   repr([x * m for x in range(start, stop + 1)]),
                   repr([x * (m + 1) for x in range(start, stop)]),
                   repr(list(range(start, stop)))]
    return _q(prompt, result, distractors,
              "The comprehension applies the expression to every value produced by range.",
              "Comprehensions", tier, "Lists")


def _list_pop(rng, tier):
    values = rng.sample(range(2, 40), rng.randint(4, 7))
    index = rng.randrange(len(values))
    result = values[:index] + values[index + 1:]
    prompt = f"What is printed?\nitems = {values!r}\nitems.pop({index})\nprint(items)"
    distractors = [repr(values), repr(values[:-1]), repr(values[::-1]), repr(values[index:])]
    return _q(prompt, repr(result), distractors,
              f"pop({index}) removes and returns the item at that index; print shows the remaining list.",
              "List methods", tier, "Lists")


def _algorithm_linear_search(rng, tier):
    values = rng.sample(range(2, 40), rng.randint(5, 8))
    target = rng.choice(values) if rng.random() < 0.7 else rng.randint(40, 60)
    result = values.index(target) if target in values else -1
    prompt = (f"What is printed?\ndef find(values, target):\n"
              "    for index, value in enumerate(values):\n"
              "        if value == target:\n            return index\n    return -1\n"
              f"print(find({values!r}, {target}))")
    distractors = _numeric_distractors(result, [0, len(values), len(values) - 1, 1], rng)
    return _q(prompt, str(result), distractors,
              "Linear search returns the first matching index, or -1 when the target is absent.",
              "Linear search", tier, "Basic Algorithms")


def _algorithm_sum(rng, tier):
    values = rng.sample(range(2, 25), rng.randint(4, 8))
    result = sum(values)
    prompt = (f"What is printed?\nvalues = {values!r}\ntotal = 0\nfor value in values:\n"
              "    total += value\nprint(total)")
    distractors = _numeric_distractors(result, [max(values), min(values), len(values)], rng)
    return _q(prompt, str(result), distractors,
              "Starting the accumulator at zero lets the loop add every value exactly once.",
              "Accumulators", tier, "Basic Algorithms")


def _algorithm_max(rng, tier):
    values = rng.sample(range(2, 60), rng.randint(4, 8))
    result = max(values)
    prompt = (f"What is printed?\nvalues = {values!r}\nbest = values[0]\nfor value in values:\n"
              "    if value > best:\n        best = value\nprint(best)")
    distractors = _numeric_distractors(result, [min(values), values[0], sum(values)], rng)
    return _q(prompt, str(result), distractors,
              "The loop replaces best whenever it sees a larger value.", "Maximum", tier, "Basic Algorithms")


def _algorithm_count(rng, tier):
    values = rng.sample(range(1, 30), rng.randint(5, 9))
    threshold = rng.randint(5, 20)
    result = sum(value > threshold for value in values)
    prompt = (f"What is printed?\nvalues = {values!r}\ncount = 0\nfor value in values:\n"
              f"    if value > {threshold}:\n        count += 1\nprint(count)")
    distractors = _numeric_distractors(result, [sum(value >= threshold for value in values),
                                                sum(value < threshold for value in values), len(values)], rng)
    return _q(prompt, str(result), distractors,
              "The counter increases only for values strictly greater than the threshold.",
              "Counting", tier, "Basic Algorithms")


def _algorithm_binary_middle(rng, tier):
    values = sorted(rng.sample(range(2, 60), rng.choice([7, 9])))
    middle = len(values) // 2
    target = rng.choice([values[0], values[middle], values[-1], rng.randint(2, 60)])
    if target == values[middle]:
        correct = "Found at the middle"
    elif target < values[middle]:
        correct = "Left half"
    else:
        correct = "Right half"
    prompt = (f"A binary search checks the middle value of {values!r} while looking for {target}. "
              "Which part is searched next?")
    return _q(prompt, correct, ["Left half", "Right half", "Found at the middle", "Search stops"],
              f"The middle value is {values[middle]}; comparing it with {target} decides the next branch.",
              "Binary search", tier, "Basic Algorithms")


def _algorithm_complexity(rng, tier):
    kind = rng.choice(["single", "half"] if tier == "foundation" else ["single", "nested", "half"])
    if kind == "single":
        code = "for i in range(n):\n    total += i"
        correct, distractors = "O(n)", ["O(1)", "O(n²)", "O(log n)"]
        explanation = "One loop over n items performs work proportional to n."
    elif kind == "half":
        code = "while n > 1:\n    n //= 2"
        correct, distractors = "O(log n)", ["O(n)", "O(n²)", "O(1)"]
        explanation = "Halving n each iteration takes logarithmically many steps."
    else:
        code = "for i in range(n):\n    for j in range(n):\n        total += 1"
        correct, distractors = "O(n²)", ["O(n)", "O(log n)", "O(1)"]
        explanation = "Nested loops each running n times perform on the order of n × n steps."
    prompt = f"What is the time complexity of this code?\n{code}"
    return _q(prompt, correct, distractors, explanation, "Complexity", tier, "Basic Algorithms")


def _algorithm_factorial(rng, tier):
    k = rng.randint(2, 6)
    result = math.factorial(k)
    prompt = (f"What is printed?\ndef f(n):\n    return 1 if n <= 1 else n * f(n - 1)\n"
              f"print(f({k}))")
    distractors = _numeric_distractors(result, [k * k, 2 ** k, k * (k - 1)], rng)
    return _q(prompt, str(result), distractors,
              "The recursive function multiplies n by the factorial of n - 1 until it reaches the base case.",
              "Recursion", tier, "Basic Algorithms")


GENERATORS = {
    "Variables": [_variables_reassignment, _variables_swap, _variables_names,
                  _variables_expression, _variables_string_length, _variables_unpacking],
    "Data Types": [_types_literal, _types_conversion, _types_operator,
                   _types_boolean, _types_concatenation, _types_rounding],
    "Conditionals": [_condition_comparison, _condition_boolean_ops, _condition_elif,
                     _condition_ternary, _condition_membership, _condition_chained],
    "Loops": [_loop_range_sum, _loop_range_count, _loop_while,
              _loop_break, _loop_continue, _loop_factorial],
    "Functions": [_function_return, _function_default, _function_keyword,
                  _function_lambda, _function_scope, _function_print_return],
    "Lists": [_list_index, _list_slice, _list_append,
              _list_sum, _list_comprehension, _list_pop],
    "Basic Algorithms": [_algorithm_linear_search, _algorithm_sum, _algorithm_max,
                         _algorithm_count, _algorithm_binary_middle,
                         _algorithm_complexity, _algorithm_factorial],
}


def resolve_topic(topic):
    """Return a supported topic name, or None for an unknown catalog topic."""
    if not topic:
        return None
    key = _clean(topic, 120).casefold()
    return TOPIC_ALIASES.get(key)


def supported_topics():
    return list(QUIZ_QUESTIONS)


def generate_offline_questions(topic, count=10, difficulty="core", rng=None, avoid_prompts=None):
    """Generate `count` unique, validated questions for a supported topic.

    `difficulty` biases the mix of foundation/core/stretch questions. Recent
    prompts can be excluded so repeated practice does not feel like memorising.
    """
    try:
        count = max(1, min(20, int(count)))
    except (TypeError, ValueError):
        count = 10
    rng = rng or random.Random()
    topic_name = resolve_topic(topic)
    if topic_name is None:
        raise ValueError(f"The offline generator supports: {', '.join(supported_topics())}.")
    difficulty = difficulty if difficulty in TIER_WEIGHTS else "core"
    weights = TIER_WEIGHTS[difficulty]
    curated = curated_bank(topic_name)
    generators = GENERATORS[topic_name]
    avoid = {_prompt_key(item) for item in (avoid_prompts or [])}
    seen = set()
    questions = []
    max_attempts = max(500, count * 80)
    for _ in range(max_attempts):
        if len(questions) >= count:
            break
        tier = rng.choices(TIERS, weights=weights, k=1)[0]
        use_curated = bool(curated) and rng.random() < 0.25
        if use_curated:
            candidates = [item for item in curated if item["difficulty"] == tier] or curated
            raw = rng.choice(candidates)
        else:
            raw = rng.choice(generators)(rng, tier)
        normalised = _normalise(raw, rng, topic_name)
        key = _prompt_key(normalised["prompt"])
        if key in seen or key in avoid:
            continue
        seen.add(key)
        questions.append(normalised)
    if len(questions) < count:
        # Prefer a full quiz over repeating recent prompts, but never repeat a
        # prompt inside the quiz itself.
        for raw in curated:
            if len(questions) >= count:
                break
            normalised = _normalise(raw, rng, topic_name)
            key = _prompt_key(normalised["prompt"])
            if key not in seen:
                seen.add(key)
                questions.append(normalised)
    if len(questions) < count:
        raise ValueError("Could not generate enough unique questions for this topic.")
    return questions
