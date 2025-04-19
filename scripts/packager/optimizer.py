from collections import deque
from functools import singledispatch, wraps
import inspect
import itertools
import math
import pickle
import signal
import random
from typing import Any, Callable, Optional, Tuple, get_args, get_origin, get_type_hints
import tqdm
from dataclasses import dataclass, replace
from multiprocessing import Pool

from packager import nodes


def mutate(root: tuple[nodes.Node, list], rand: random.Random):
    """
    Mutates an abstract syntax tree by making small modification to it, e.g.
    flipping binary operators or changing variable names
        Parameters:
            root (nodes.Node): First item is the root of the
                abstract syntax tree. These will get modified, so deep
                copy them before calling this function if needed.
            rand (random.Random): Random number generator to use
    """
    root
    mutations = []
    def _check_mutations(node: nodes.Node, parent: nodes.Node, attr: str):
        if type(node) == nodes.Alternative:
            for i, _ in enumerate(node.alternatives[1:]):
                def _mutation(i=i):
                    node.alternatives[0], node.alternatives[i + 1] = node.alternatives[i + 1], node.alternatives[0]
                mutations.append(_mutation)
        elif type(node) == nodes.Reorder:
            for i in range(len(node.statements)):
                for j in range(i + 1, len(node.statements)):
                    def _mutation(i=i, j=j):
                        node.statements[i], node.statements[j] = node.statements[j], node.statements[i]
                    mutations.append(_mutation)
    visit(root, _check_mutations)
    if len(mutations) > 0:
        mutation = rand.choice(mutations)
        mutation()


class Solutions:
    processes: int
    queue: deque
    mutate_func: Callable[[Any], Any]
    cost_func: Callable[[Any, int], Tuple[int, Any]]
    init_state: Any
    queue_length: int

    def __init__(self, state, seed: int, queue_length: int, processes: int, cost_func: Callable[[Any, int], Tuple[int, Any]], best_func, init=None, initargs=()):
        self.processes = processes
        if processes != 1:
            self.pool = Pool(processes=processes, initializer=_PoolInitializer(init), initargs=(initargs,))
        else:
            self.pool = None
        self.queue = deque()
        self.cost_func = cost_func
        self.cost_func_pickled = pickle.dumps(self.cost_func)
        self.queue_length = queue_length
        self.init_state = pickle.dumps(state)
        self.seed = seed
        self.best_func = best_func

    def __enter__(self):
        if self.pool is not None:
            self.pool.__enter__()

        rng = random.Random(self.seed)
        for i in range(self.queue_length):
            if self.pool is not None:
                self.put(self.init_state, pickle.dumps(rng), first=i == 0)
            else:
                self.put(self.init_state, pickle.loads(pickle.dumps(rng)), first=i == 0)
            rng = random.Random(rng.getrandbits(32))  # shuffle the rng so that the different rngs are used
        return self

    def __exit__(self, *args):
        if self.pool is not None:
            self.pool.close()
            self.pool.join()
            self.pool.__exit__(*args)

    def get(self):
        if self.pool is not None:
            return self.queue.popleft().get(timeout=9999)
        else:
            state, rng, first = self.queue.popleft()
            return _mutate_cost(state, rng, self.cost_func, first)

    def put(self, state: Any, rng: random.Random, first=False):
        if self.pool is not None:
            self.queue.append(self.pool.apply_async(_mutate_cost_pickled, (state, rng, self.cost_func_pickled, first)))
        else:
            self.queue.append((state, rng, first))

    def best(self, state, cost):
        self.best_func(state, cost)


def anneal(solutions: Solutions, steps: int, start_temp: float, end_temp: float, seed: int = 0) -> Any:
    """
    Perform simulated annealing optimization, using exponential temperature schedule.
    See https://en.wikipedia.org/wiki/Simulated_annealing
        Parameters:
            solutions (Solutions): the Solutions object with a pool of solutions, cost function and best function
            steps (int): how many steps the optimization algorithms takes
            start_temp (float): starting temperature for the optimization
            end_temp (float): end temperature for the optimization
            seed (int): seed for the random number generator
        Returns:
            best (Any): The best solution found
    """
    state, current_cost, rng = solutions.get()
    solutions.best(state, current_cost)
    best_cost = current_cost
    best = state
    r = random.Random(seed)  # deterministic seed, to have deterministic results
    bar = tqdm.tqdm(_stepsGenerator(steps), position=1, leave=False)
    for i in bar:
        solutions.put(state, rng)
        alpha = i / (steps - 1)
        temp = math.exp((1 - alpha) * math.log(start_temp) + alpha * math.log(end_temp))
        candidate, cand_cost, rng = solutions.get()
        if cand_cost < current_cost or math.exp(-(cand_cost - current_cost) / temp) >= r.random():
            current_cost = cand_cost
            state = candidate
        if cand_cost < best_cost:
            best_cost = cand_cost
            best = candidate
            solutions.best(best, best_cost)
        bar.set_description(f"B:{best_cost} C:{current_cost} A:{cand_cost} T: {temp:.1f}")
        if best_cost <= 0:
            break
    return pickle.loads(best)


def lahc(solutions: Solutions, steps: int, list_length: int, init_margin: int) -> Any:
    """
    Optimize a function using Late Acceptance Hill Climbing
    See https://arxiv.org/pdf/1806.09328.pdf
        Parameters:
            solutions (Solutions): the Solutions object with a pool of solutions, cost function and best function
            steps (int): how many steps the optimization algorithms takes
            list_length (int): length of the history in the algorithm
            init_margin (int): how much margin, in bytes, to add to the initial best cost
        Returns:
            best (Any): The best solution found
    """
    state, current_cost, rng = solutions.get()
    solutions.best(state, current_cost)
    best_cost = current_cost
    history = [best_cost + init_margin] * list_length
    best = state
    bar = tqdm.tqdm(_stepsGenerator(steps), position=1, leave=False)
    for i in bar:
        solutions.put(state, rng)
        candidate, cand_cost, rng = solutions.get()
        v = i % list_length
        if cand_cost < history[v] or cand_cost <= current_cost:
            current_cost = cand_cost
            state = candidate
        if current_cost < history[v]:
            history[v] = current_cost
        if cand_cost < best_cost:
            best_cost = cand_cost
            best = candidate
            solutions.best(best, best_cost)
        bar.set_description(f"B:{best_cost} C:{current_cost} A:{cand_cost}")
        if best_cost <= 0:
            break
    return pickle.loads(best)


def dlas(solutions: Solutions, steps: int, list_length: int, init_margin: int) -> Any:
    """
    Optimize a function using Diversified Late Acceptance Search
    See https://arxiv.org/pdf/1806.09328.pdf
        Parameters:
            solutions (Solutions): the Solutions object with a pool of solutions, cost function and best function
            steps (int): how many steps the optimization algorithms takes
            list_length (int): length of the history in the algorithm
            init_margin (int): how much margin, in bytes, to add to the initial best cost
        Returns:
            best (Any): The best solution found
    """
    state, current_cost, rng = solutions.get()
    solutions.best(state, current_cost)
    best_cost = current_cost
    cost_max = best_cost + init_margin
    history = [cost_max] * list_length
    N = list_length
    best = state
    bar = tqdm.tqdm(_stepsGenerator(steps), position=1, leave=False)
    for i in bar:
        solutions.put(state, rng)
        prev_cost = current_cost
        candidate, cand_cost, rng = solutions.get()
        v = i % list_length
        if cand_cost == current_cost or cand_cost < cost_max:
            current_cost = cand_cost
            state = candidate
        if current_cost > history[v]:
            history[v] = current_cost
        elif current_cost < history[v] and current_cost < prev_cost:
            if history[v] == cost_max:
                N -= 1
            history[v] = current_cost
            if N <= 0:
                cost_max = max(history)
                N = history.count(cost_max)
        if cand_cost < best_cost:
            best_cost = cand_cost
            best = candidate
            solutions.best(best, best_cost)
        bar.set_description(f"B:{best_cost} C:{current_cost} M:{cost_max} A:{cand_cost}")
        if best_cost <= 0:
            break
    return pickle.loads(best)


@dataclass
class _PoolInitializer:
    """
    This class was just a simple lambda function, but it is not possible to pickle lambda functions with default pickling
    """
    init: Callable[[Any], None]

    def __call__(self, a):
        # ignore SIGINT in the pool processes; rather, let the main process handle it and close the pool when it happens
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if self.init is not None:
            self.init(a)


def _mutate_cost(state, rng: random.Random, cost_func, first):
    """
    Helper function that mutates a state and calculates the cost. Used when not
    doing multiprocessing. Avoids unnecessary pickling/unpickling of the rng and
    the cost_func.
    """
    state = pickle.loads(state)
    if not first:
        mutate(state, rng)
    new_cost = cost_func(state)
    return pickle.dumps(state), new_cost, rng


def _mutate_cost_pickled(state, rng, cost_func, first):
    """
    Helper function that mutates a state and calculates the cost. Used when
    multiprocessing. Pickles/unpickles also the rng and cost_func as these need
    to go back and forth between the main process and the pool processes.
    """
    rng = pickle.loads(rng)
    state = pickle.loads(state)
    if not first:
        mutate(state, rng)
    new_cost = pickle.loads(cost_func)(state)
    return pickle.dumps(state), new_cost, pickle.dumps(rng)


def _stepsGenerator(steps: int):
    """
    Generator for the steps of the optimization algorithms, taking into account that 0 means infinite steps
    """
    if steps == 0:
        return itertools.count()
    else:
        return range(steps)


def apply_trans(node: nodes.Node, trans: Callable[[nodes.Node], nodes.Node]) -> nodes.Node:
    """
    Applies a transformation to an abstract syntax tree recursively
        Parameters:
            node (nodes.Node): Root of the syntax tree to transform
            trans (Callable[[nodes.Node], nodes.Node]): Callback function that takes a node and returns a transformed node
        Returns:
            new_node (nodes.Node): Root of the new, transformed abstract syntax tree
    """
    if node is None:
        return trans(node)
    replaces = dict()
    try:
        for name, typehint in get_type_hints(node).items():
            attr = getattr(node, name)
            origin = get_origin(typehint)
            args = get_args(typehint)
            if origin is Optional:
                if attr is None:
                    continue
                origin = args
            if origin is list and len(args) > 0 and issubclass(args[0], nodes.Node):
                replaces[name] = [apply_trans(e, trans) for e in attr]
            elif inspect.isclass(typehint) and issubclass(typehint, nodes.Node):
                replaces[name] = apply_trans(attr, trans)
    except TypeError:
        pass
    return trans(replace(node, **replaces))


@singledispatch
def visit(node: nodes.Node, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    """
    Visit each node of an abstract syntax tree recursively
        Parameters:
            node (nodes.Node): A (root) node of the syntax tree to visit
            visitor (Callable[[nodes.Node, nodes.Node, str], None]): Callback function called for each node
    """
    if node != None:
        visitor(node, parent, attr)


@ visit.register
def _(node: nodes.Block, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)
    for s in node.statements:
        visit(s, visitor)


@ visit.register
def _(node: nodes.Alternative, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)
    for i, a in enumerate(node.alternatives):
        visit(a, visitor, node, f"alternatives.{i}")


@ visit.register
def _(node: nodes.Reorder, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)
    for i, s in enumerate(node.statements):
        visit(s, visitor, node, f"statements.{i}")


@ visit.register
def _(node: nodes.UnparsedCode, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)


# TODO: Convert to blocks?
@ visit.register
def _(node: nodes.IfDef, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)
    for i, s in enumerate(node.statements):
        visit(s, visitor, node, f"statements.{i}")


# TODO: Remove before optimizing?
@ visit.register
def _(node: nodes.Comment, visitor: Callable[[nodes.Node, nodes.Node, str], None], parent: nodes.Node = None, attr: str = None):
    visitor(node, parent, attr)
