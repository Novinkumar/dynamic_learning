"""Deterministic Python curriculum shared by seeding and answer feedback."""

TOPICS = [
    ("Variables", "Names, values, assignment, and readable code."),
    ("Data Types", "Numbers, strings, booleans, and conversions."),
    ("Conditionals", "Making decisions with if, elif, and else."),
    ("Loops", "Repeating work with for and while loops."),
    ("Functions", "Reusable blocks with parameters and return values."),
    ("Lists", "Ordered collections and common list operations."),
    ("Basic Algorithms", "Step-by-step solutions using core Python patterns."),
]

PREREQUISITES = [
    ("Data Types", "Variables"),
    ("Conditionals", "Variables"),
    ("Conditionals", "Data Types"),
    ("Loops", "Variables"),
    ("Loops", "Conditionals"),
    ("Functions", "Variables"),
    ("Functions", "Conditionals"),
    ("Lists", "Data Types"),
    ("Basic Algorithms", "Loops"),
    ("Basic Algorithms", "Functions"),
    ("Basic Algorithms", "Lists"),
]

# Each topic has a focused explanation, a worked practice page, and a challenge.
RESOURCE_CATALOG = {
    "Variables": [
        ("https://docs.python.org/3/tutorial/introduction.html#using-python-as-a-calculator", "article", 1, 12, "Learn assignment, variable names, and using stored values in expressions."),
        ("https://www.programiz.com/python-programming/variables-constants-literals", "exercise", 2, 20, "Trace assignments and practise naming and updating Python variables."),
        ("https://exercism.org/tracks/python/exercises/guidos-gorgeous-lasagna", "exercise", 3, 30, "Use named values and arithmetic to build a cooking-time calculator."),
    ],
    "Data Types": [
        ("https://docs.python.org/3/library/stdtypes.html", "article", 1, 15, "Explore integers, floats, strings, booleans, and their supported operations."),
        ("https://www.programiz.com/python-programming/type-conversion-and-casting", "exercise", 2, 20, "Work through implicit and explicit conversions with Python examples."),
        ("https://exercism.org/tracks/python/exercises/currency-exchange", "exercise", 3, 30, "Apply numeric types and conversions to currency calculations."),
    ],
    "Conditionals": [
        ("https://docs.python.org/3/tutorial/controlflow.html#if-statements", "article", 1, 12, "Read how if, elif, and else select a branch based on a condition."),
        ("https://www.programiz.com/python-programming/if-elif-else", "exercise", 2, 20, "Practise comparisons, branching, and nested decisions."),
        ("https://exercism.org/tracks/python/exercises/ghost-gobble-arcade-game", "exercise", 3, 30, "Combine boolean conditions to implement arcade-game rules."),
    ],
    "Loops": [
        ("https://docs.python.org/3/tutorial/controlflow.html#for-statements", "article", 1, 12, "Learn iteration, range, break, and continue in Python loops."),
        ("https://www.programiz.com/python-programming/while-loop", "exercise", 2, 20, "Trace while loops and update conditions to avoid infinite repetition."),
        ("https://exercism.org/tracks/python/exercises/grade-school", "exercise", 3, 30, "Practise iterating over collections to organise school rosters."),
    ],
    "Functions": [
        ("https://docs.python.org/3/tutorial/controlflow.html#defining-functions", "article", 1, 15, "Define reusable functions with parameters, return values, and defaults."),
        ("https://www.programiz.com/python-programming/function", "exercise", 2, 20, "Write and call functions, and distinguish return values from printed output."),
        ("https://exercism.org/tracks/python/exercises/black-jack", "exercise", 3, 30, "Break card-scoring logic into small reusable functions."),
    ],
    "Lists": [
        ("https://docs.python.org/3/tutorial/datastructures.html#more-on-lists", "article", 1, 15, "Explore indexing, slicing, appending, and common list methods."),
        ("https://www.programiz.com/python-programming/list", "exercise", 2, 20, "Practise reading and changing ordered collections."),
        ("https://exercism.org/tracks/python/exercises/list-ops", "exercise", 3, 30, "Implement transformations and reductions on lists."),
    ],
    "Basic Algorithms": [
        ("https://www.programiz.com/dsa/algorithm", "article", 1, 15, "Understand step-by-step problem solving and algorithm design."),
        ("https://docs.python.org/3/tutorial/datastructures.html#looping-techniques", "exercise", 2, 20, "Use iteration patterns to scan, compare, and accumulate values."),
        ("https://exercism.org/tracks/python/exercises/binary-search", "exercise", 3, 35, "Implement a search algorithm and reason about its prerequisites."),
    ],
}

# Tuples contain a prompt, options, the correct option, and a teaching explanation.
# Explanations live here rather than adding a column to existing development DBs.
QUIZ_QUESTIONS = {
    "Variables": [
        ("What is printed by this Python code?\nx = 4\nx = x + 3\nprint(x)", ["4", "7", "3", "43"], "7", "The second assignment adds 3 to the existing value 4, then stores 7 in x."),
        ("Which is a valid Python variable name?", ["2score", "player_score", "player-score", "class"], "player_score", "Names may contain letters, digits, and underscores, but cannot start with a digit or use a reserved keyword."),
        ("What is printed?\na = 5\nb = a\na = 9\nprint(b)", ["5", "9", "14", "None"], "5", "b receives the integer value 5. Reassigning a does not reassign b."),
        ("Which statement assigns the number 10 to count?", ["count == 10", "10 = count", "count = 10", "count: 10"], "count = 10", "A single equals sign assigns a value; a double equals sign compares two values."),
    ],
    "Data Types": [
        ("What is the type of the value 3.5?", ["int", "float", "str", "bool"], "float", "A number with a fractional component such as 3.5 is a float."),
        ("What is printed by print(int('8') + 2)?", ["82", "10", "8", "A TypeError"], "10", "int converts the text '8' into the integer 8, so numeric addition produces 10."),
        ("What is printed by print('Py' + 'thon')?", ["Python", "Py thon", "A TypeError", "6"], "Python", "Adding two strings concatenates them without inserting a space."),
    ],
    "Conditionals": [
        ("What is printed?\nx = 8\nif x > 10:\n    print('large')\nelif x > 5:\n    print('medium')\nelse:\n    print('small')", ["large", "medium", "small", "Nothing"], "medium", "8 is not greater than 10 but is greater than 5, so only the elif branch runs."),
        ("Which condition is true when age is 16?", ["age >= 18", "age < 18", "age == 18", "age > 21"], "age < 18", "The value 16 is less than 18; the other comparisons are false."),
        ("What is printed?\nready = True\nif ready:\n    print('go')\nelse:\n    print('wait')", ["go", "wait", "go then wait", "True"], "go", "A true condition executes the if branch and skips the else branch."),
        ("Which operator checks whether both conditions are true?", ["or", "not", "and", "="], "and", "and is true only when both operands are true; or needs only one true operand."),
    ],
    "Loops": [
        ("What is printed?\ntotal = 0\nfor n in range(1, 4):\n    total += n\nprint(total)", ["3", "6", "10", "4"], "6", "range(1, 4) yields 1, 2, and 3. Their sum is 6; the stop value 4 is excluded."),
        ("How many times does this loop run?\nfor i in range(3):\n    print(i)", ["2", "3", "4", "Forever"], "3", "range(3) yields 0, 1, and 2, which gives three iterations."),
        ("What does break do inside a loop?", ["Skips only the current iteration", "Exits the nearest loop", "Restarts the loop", "Ends every function"], "Exits the nearest loop", "break immediately leaves the nearest enclosing loop; continue skips only one iteration."),
        ("What is printed?\nn = 3\nwhile n > 0:\n    n -= 1\nprint(n)", ["3", "1", "0", "-1"], "0", "The loop subtracts one until n becomes 0, when n > 0 is false."),
    ],
    "Functions": [
        ("What is printed?\ndef double(n):\n    return n * 2\nprint(double(3))", ["3", "6", "None", "double(3)"], "6", "The argument 3 becomes parameter n, and the function returns 3 multiplied by 2."),
        ("Which keyword sends a result back to a function's caller?", ["print", "break", "return", "pass"], "return", "return ends the function call and provides its result to the caller."),
        ("What does a Python function return if it has no return statement?", ["0", "False", "None", "An empty string"], "None", "A function that reaches its end without an explicit return returns None."),
        ("What is printed?\ndef greet(name='Ada'):\n    return 'Hi ' + name\nprint(greet())", ["Hi Ada", "Hi name", "Hi", "A TypeError"], "Hi Ada", "When no argument is supplied, the default parameter value 'Ada' is used."),
    ],
    "Lists": [
        ("What is printed?\nitems = ['a', 'b', 'c']\nprint(items[1])", ["a", "b", "c", "An IndexError"], "b", "Python list indexing starts at zero, so index 1 selects the second element."),
        ("What is printed?\nitems = [1, 2]\nitems.append(3)\nprint(len(items))", ["2", "3", "6", "None"], "3", "append adds one element to the end of the list, making its length 3."),
        ("Which expression selects the last item of a nonempty list called items?", ["items[0]", "items[-1]", "items[len(items)]", "items.last()"], "items[-1]", "Negative indices count from the end; -1 selects the last element."),
    ],
    "Basic Algorithms": [
        ("Which initial value should total have when adding all numbers in a list?", ["0", "1", "None", "The last number"], "0", "Zero is the additive identity, so starting at zero includes every number exactly once."),
        ("What is the worst-case number of items checked by linear search in a list of n items?", ["1", "n", "n * n", "0"], "n", "If the target is absent or last, linear search checks every one of the n items."),
        ("What must be true before using binary search on a list?", ["The list is sorted", "The list has no numbers", "The list has exactly two items", "The list is empty"], "The list is sorted", "Binary search discards half the search space using the ordering of a sorted list."),
    ],
}


def question_explanation(question):
    # Generated questions carry their own teacher-written/model-written
    # explanation. Curated questions keep the original lookup so existing
    # databases without the explanation column still receive feedback.
    stored = (getattr(question, "explanation", "") or "").strip()
    if stored:
        return stored
    for questions in QUIZ_QUESTIONS.values():
        for prompt, _, answer, explanation in questions:
            if prompt == question.prompt and answer == question.answer:
                return explanation
    return f"The correct answer is {question.answer}. Review this concept before trying again."
