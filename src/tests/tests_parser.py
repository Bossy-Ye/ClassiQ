from Framework.parser import ProblemParser
from Framework.generator import QASMGenerator
import json
import utils

# Load the test cases from the JSON file
with open('//cases/classical_cases/cases.json',
          'r') as f:
    data = json.load(f)
generator = QASMGenerator()
# Access and execute the code for the clique problem
clique_code = data['test_cases']['clique']
maxcut_code = data['test_cases']['maximum cut']
eigenvalue_code = data['test_cases']['eigenvalue']
svm_code = data['test_cases']['svm']
cnf_code = data['test_cases']['cnf']
addition_code = data['test_cases']['addition']
independent_set_code = data['test_cases']['independent set']
tsp_code = data['test_cases']['tsp']
coloring_code = data['test_cases']['coloring']
triangle_finding_code = data['test_cases']['triangle finding']
vrp_code = data['test_cases']['vrp']
factor_code = data['test_cases']['factor']

parser = ProblemParser()
parser.parse_code(clique_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

print(maxcut_code)
parser.parse_code(maxcut_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)


parser.parse_code(eigenvalue_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)
observable = utils.decompose_into_pauli(parser.data)
print(observable)

parser.parse_code(svm_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)


parser.parse_code(cnf_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)


parser.parse_code(independent_set_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

# qasm_code = generator.qasm_generate(classical_code=independent_set_code, verbose=False)
# print(qasm_code.get('grover'))

parser.parse_code(tsp_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

parser.parse_code(coloring_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

parser.parse_code(addition_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

parser.parse_code(triangle_finding_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

parser.parse_code(vrp_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)

parser.parse_code(factor_code)
print(parser.problem_type, parser.specific_graph_problem, parser.data)