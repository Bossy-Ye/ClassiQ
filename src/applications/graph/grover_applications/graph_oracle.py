from itertools import combinations

import networkx as nx
import qiskit.qasm2
from matplotlib import pyplot as plt
from pysat.formula import CNF
from qiskit.circuit.library import PhaseOracle

import numpy as np
from qiskit import QuantumCircuit, Aer, execute
import matplotlib.pyplot as plt
# Example CNF Formula using PySAT
from qiskit.circuit.library import OR


def cnf_to_quantum_circuit_optimized(cnf_formula):
    """
    Converts a CNF formula into a quantum circuit with optimized logic and correct carry management.

    Parameters
    ----------
    cnf_formula: A CNF formula object
        The CNF formula to convert into a quantum circuit.
        The CNF formula consists of a list of clauses, where each clause is a list of literals.
        A literal is a positive or negative integer representing a variable or its negation.

    Returns
    -------
    qc : QuantumCircuit
        The quantum circuit that represents the CNF formula.
    """
    num_vars = cnf_formula.nv  # Number of variables
    num_clauses = len(cnf_formula.clauses)

    # Number of qubits required to count up to the number of clauses
    num_count_qubits = (num_clauses).bit_length()  # log2(num_clauses + 1) rounded up

    # Create a quantum circuit with input qubits, count ancillas, and 1 final output qubit
    qc = QuantumCircuit(num_vars + num_count_qubits + 1 + 1)  # +1 for the final output qubit + 1 for the final result

    # Ancilla qubits to store the count of satisfied clauses
    count_ancillas = list(range(num_vars, num_vars + num_count_qubits))
    final_ancilla = num_vars + num_count_qubits

    final_result = final_ancilla + 1
    # Initialize the final ancilla qubit to |1⟩ (assume all clauses are satisfied)
    #qc.x(final_ancilla)

    for i, clause in enumerate(cnf_formula.clauses):
        clause_qubits = []
        clause_negations = []

        # Step through each literal in the clause
        for lit in clause:
            qubit_index = abs(lit) - 1  # Convert variable index to qubit index
            if lit < 0:  # If the literal is negative (~x)
                qc.x(qubit_index)  # Apply X to flip qubit before using in OR
                clause_negations.append(qubit_index)
            clause_qubits.append(qubit_index)

        # OR gate for the clause, outputting to a temporary ancilla qubit
        clause_ancilla = num_vars + num_count_qubits
        or_gate = OR(len(clause_qubits))
        qc.append(or_gate, clause_qubits + [clause_ancilla])

        # Increment logic with proper carry management
        # Start with the least significant bit
        # qc.cx(clause_ancilla, count_ancillas[0])
        # For subsequent bits, handle the carry propagation
        for j in range(1, num_count_qubits):
            control_qubits = [clause_ancilla]
            for i in range(len(count_ancillas)-j):
                control_qubits.append(count_ancillas[i])
            qc.mcx(control_qubits, count_ancillas[-j])
            # Propagate the carry from the lower bits
            #qc.mcx()
            #qc.ccx(clause_ancilla, count_ancillas[j - 1], count_ancillas[j])
        qc.cx(clause_ancilla, count_ancillas[0])
        # Uncompute the OR gate
        qc.append(or_gate.inverse(), clause_qubits + [clause_ancilla])

        # Revert any negations
        if clause_negations:
            qc.x(clause_negations)
        qc.barrier()

    # Final comparison: Check if the count matches the total number of clauses
    # Convert the number of clauses to binary and compare with the ancillas
    control_qubits = []
    for j in range(num_count_qubits):
        if (num_clauses >> j) & 1:
            control_qubits.append(count_ancillas[j])
            #qc.cx(count_ancillas[j], final_ancilla)
    #print(count_ancillas)
    qc.mcx(control_qubits, final_ancilla)
    qc.cx(final_ancilla, final_result)
    qc.reset(count_ancillas)
    qc.reset(final_ancilla)
    # If the count matches the number of clauses, final_ancilla will remain |1⟩
    # If not, it will be flipped to |0⟩
    return qc


def cnf_to_quantum_circuit(cnf_formula):
    num_vars = cnf_formula.nv  # Number of variables
    num_clauses = len(cnf_formula.clauses)

    # Create a quantum circuit with num_vars input qubits, num_clauses output qubits, and 1 final ancilla qubit
    qc = QuantumCircuit(num_vars + num_clauses + 1)  # +1 for the final ancilla

    # List to keep track of output qubits for each clause
    clause_outputs = []
    or_gates = []  # To keep track of the OR gates for uncomputing
    negations = []  # To keep track of which qubits were negated

    # Step through each clause and create an OR gate
    for i, clause in enumerate(cnf_formula.clauses):
        clause_qubits = []
        clause_negations = []
        for lit in clause:
            qubit_index = abs(lit) - 1  # Convert variable index to qubit index
            if lit < 0:  # If the literal is negative (~x)
                qc.x(qubit_index)  # Apply X to flip qubit before using in OR
                clause_negations.append(qubit_index)
            clause_qubits.append(qubit_index)

        # OR gate for the clause, outputting to an ancillary qubit
        or_gate = OR(len(clause_qubits))
        output_qubit = num_vars + i  # Assign output qubit from the ancillary pool
        clause_outputs.append(output_qubit)

        # Apply the OR gate: inputs are the qubits from the clause, output is the clause output qubit
        qc.append(or_gate, clause_qubits + [output_qubit])

        if clause_negations:
            qc.x(clause_negations)

        # Add a barrier after applying the OR gate and any necessary re-negations
        qc.barrier()

        # Store the OR gate and negations for uncomputing
        or_gates.append((or_gate, clause_qubits, output_qubit))
        negations.append(clause_negations)

    # Combine all clause outputs into the final oracle condition
    qc.mcx(clause_outputs, num_vars + num_clauses)

    # Add a barrier after applying the multi-controlled X gate
    qc.barrier()

    # Uncompute the OR gates by applying them in reverse order
    for i, (or_gate, clause_qubits, output_qubit) in enumerate(reversed(or_gates)):
        qc.barrier()
        for qubit_index in negations[-(i + 1)]:
            qc.x(qubit_index)
        qc.append(or_gate.inverse(), clause_qubits + [output_qubit])

        # Apply X gates to revert any negated qubits back to their original state
        for qubit_index in negations[-(i + 1)]:
            qc.x(qubit_index)
    qc.barrier()
    return qc


def cnf_to_quantum_oracle(cnf_formula):
    # Create the initial quantum circuit
    qc = cnf_to_quantum_circuit(cnf_formula)

    # Create an empty quantum circuit to hold the full oracle operations
    qc_tmp = QuantumCircuit(qc.num_qubits)

    qc_tmp.barrier()
    # Prepare the final ancilla qubit in the |-> state
    qc_tmp.x(qc.num_qubits - 1)
    qc_tmp.h(qc.num_qubits - 1)
    qc_tmp.barrier()

    # Append the CNF quantum circuit (the oracle construction)
    qc_tmp.compose(qc, inplace=True)

    # Flip the phase of the ancilla qubit back
    qc_tmp.h(qc.num_qubits - 1)
    qc_tmp.x(qc.num_qubits - 1)

    qc_tmp.barrier()
    return qc_tmp


def cnf_to_quantum_oracle_optimized(cnf_formula):
    qc = cnf_to_quantum_circuit_optimized(cnf_formula)
    # Create an empty quantum circuit to hold the full oracle operations
    qc_tmp = QuantumCircuit(qc.num_qubits)

    qc_tmp.barrier()
    # Prepare the final ancilla qubit in the |-> state
    qc_tmp.x(qc.num_qubits - 1)
    qc_tmp.h(qc.num_qubits - 1)
    qc_tmp.barrier()

    # Append the CNF quantum circuit (the oracle construction)
    qc_tmp.compose(qc, inplace=True)

    # Flip the phase of the ancilla qubit back
    qc_tmp.h(qc.num_qubits - 1)
    qc_tmp.x(qc.num_qubits - 1)

    qc_tmp.barrier()
    return qc_tmp


def graph_coloring_to_sat(graph: nx.Graph, num_colors: int) -> CNF:
    """
    Converts a graph coloring problem into a 3-SAT problem.

    Parameters:
    - graph (nx.Graph): A networkx graph.
    - num_colors (int): Number of colors available for coloring the graph.

    Returns:
    - CNF: A CNF object representing the 3-SAT problem.
    """
    cnf = CNF()
    variables = {}
    counter = 1

    # Step 1: Create variables x_{v,c} for each vertex v and each color c
    for v in graph.nodes():
        for c in range(1, num_colors + 1):
            variables[(v, c)] = counter
            counter += 1

    # Step 2: Add constraints that each vertex must have at least one color
    for v in graph.nodes():
        clause = [variables[(v, c)] for c in range(1, num_colors + 1)]
        cnf.append(clause)

    # Step 3: Add constraints that no two adjacent vertices share the same color
    for u, v in graph.edges():
        for c in range(1, num_colors + 1):
            cnf.append([-variables[(u, c)], -variables[(v, c)]])

    return cnf


def independent_set_to_sat(graph: nx.Graph) -> CNF:
    """
    Converts an Independent Set problem into a SAT problem in CNF format.

    Parameters:
    - graph (nx.Graph): A NetworkX graph.

    Returns:
    - CNF: A CNF object representing the SAT problem.
    """
    cnf = CNF()
    n = len(graph.nodes)

    # Variables: x_i where i is the vertex index
    var = lambda i: i + 1  # Variables indexed from 1

    # Clause 1: For every edge (u, v), add a clause that at least one of them must not be in the independent set
    for u, v in graph.edges():
        cnf.append([-var(u), -var(v)])

    return cnf


def clique_to_sat(graph: nx.Graph, k: int) -> CNF:
    """
    Converts the k-Clique problem to a SAT problem.

    Parameters:
        graph (nx.Graph): The input graph.
        k (int): The size of the clique to find.

    Returns:
        CNF: The SAT formula in CNF representing the k-Clique problem.
    """
    cnf = CNF()
    n = len(graph.nodes)

    # Variables: x_iv where i is the position in the clique and v is the vertex
    var = lambda i, v: i * n + v + 1  # Create unique variables (i is 0-based, v is 0-based)

    # Clause 1: Each position in the clique must be occupied by exactly one vertex
    # \frac{n^2 k + nk}{2} clauses
    for i in range(k):
        # At least one vertex occupies the i-th position in the clique
        cnf.append([var(i, v) for v in range(n)])
        # No more than one vertex occupies the i-th position in the clique
        for v in range(n):
            for u in range(v + 1, n):
                cnf.append([-var(i, v), -var(i, u)])

    # Clause 2: No vertex can occupy more than one position in the clique
    # \frac{k^2 n - nk}{2} clauses
    for v in range(n):
        for i in range(k):
            for j in range(i + 1, k):
                cnf.append([-var(i, v), -var(j, v)])

    # Clause 3: All vertices in the clique must be connected by an edge
    # \(k^2-k\)\(\frac{n^2-n}{2}-|E|\) clauses
    for i in range(k):
        for j in range(i + 1, k):
            for v in range(n):
                for u in range(n):
                    if v != u and not graph.has_edge(v, u):
                        cnf.append([-var(i, v), -var(j, u)])
    return cnf
