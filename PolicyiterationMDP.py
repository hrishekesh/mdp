#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun  8 05:26:45 2019

@author: hrishekesh.shinde
"""

import random
import operator
import time

orientations = EAST, NORTH, WEST, SOUTH = [(1, 0), (0, 1), (-1, 0), (0, -1)]
turns = LEFT, RIGHT = (+1, -1)
argmax = max

def vector_add(a, b):
    """Component-wise addition of two vectors."""
    return tuple(map(operator.add, a, b))

def turn_heading(heading, inc, headings=orientations):
    return headings[(headings.index(heading) + inc) % len(headings)]

def turn_right(heading):
    return turn_heading(heading, RIGHT)


def turn_left(heading):
    return turn_heading(heading, LEFT)

class MDP:

    """A Markov Decision Process, defined by an initial state, transition model,
    and reward function. We also keep track of a gamma value, for use by
    algorithms. The transition model is represented somewhat differently from
    the text. Instead of P(s' | s, a) being a probability number for each
    state/state/action triplet, we instead have T(s, a) return a
    list of (p, s') pairs. We also keep track of the possible states,
    terminal states, and actions for each state. [page 646]"""

    def __init__(self, init, actlist, terminals, transitions=None, reward=None, states=None, gamma=0.9):
        if not (0 < gamma <= 1):
            raise ValueError("An MDP must have 0 < gamma <= 1")

        # collect states from transitions table if not passed.
        self.states = states or self.get_states_from_transitions(transitions)
            
        self.init = init
        
        if isinstance(actlist, list):
            # if actlist is a list, all states have the same actions
            self.actlist = actlist

        elif isinstance(actlist, dict):
            # if actlist is a dict, different actions for each state
            self.actlist = actlist
        
        self.terminals = terminals
        self.transitions = transitions or {}
        if not self.transitions:
            print("Warning: Transition table is empty.")

        self.gamma = gamma

        self.reward = reward or {s: 0 for s in self.states}

        # self.check_consistency()

    def R(self, state):
        """Return a numeric reward for this state."""

        return self.reward[state]

    def T(self, state, action):
        """Transition model. From a state and an action, return a list
        of (probability, result-state) pairs."""

        if not self.transitions:
            raise ValueError("Transition model is missing")
        else:
            return self.transitions[state][action]

    def actions(self, state):
        """Return a list of actions that can be performed in this state. By default, a
        fixed list of actions, except for terminal states. Override this
        method if you need to specialize by state."""

        if state in self.terminals:
            return [None]
        else:
            return self.actlist

    def get_states_from_transitions(self, transitions):
        if isinstance(transitions, dict):
            s1 = set(transitions.keys())
            s2 = set(tr[1] for actions in transitions.values()
                     for effects in actions.values()
                     for tr in effects)
            return s1.union(s2)
        else:
            print('Could not retrieve states from transitions')
            return None

    def check_consistency(self):

        # check that all states in transitions are valid
        assert set(self.states) == self.get_states_from_transitions(self.transitions)

        # check that init is a valid state
        assert self.init in self.states

        # check reward for each state
        assert set(self.reward.keys()) == set(self.states)

        # check that all terminals are valid states
        assert all(t in self.states for t in self.terminals)

        # check that probability distributions for all actions sum to 1
        for s1, actions in self.transitions.items():
            for a in actions.keys():
                s = 0
                for o in actions[a]:
                    s += o[0]
                assert abs(s - 1) < 0.001

class GridMDP(MDP):

    """A two-dimensional grid MDP, as in [Figure 17.1]. All you have to do is
    specify the grid as a list of lists of rewards; use None for an obstacle
    (unreachable state). Also, you should specify the terminal states.
    An action is an (x, y) unit vector; e.g. (1, 0) means move east."""

    def __init__(self, grid, terminals, init=(0, 0), gamma=.9):
        grid.reverse()     # because we want row 0 on bottom, not on top
        reward = {}
        states = set()
        self.rows = len(grid)
        self.cols = len(grid[0])
        self.grid = grid
        for x in range(self.cols):
            for y in range(self.rows):
                if grid[y][x]:
                    states.add((x, y))
                    reward[(x, y)] = grid[y][x]
        self.states = states
        actlist = orientations
        transitions = {}
        for s in states:
            transitions[s] = {}
            for a in actlist:
                transitions[s][a] = self.calculate_T(s, a)
        MDP.__init__(self, init, actlist=actlist,
                     terminals=terminals, transitions=transitions, 
                     reward=reward, states=states, gamma=gamma)

    def calculate_T(self, state, action):
        if action:
            return [(0.8, self.go(state, action)),
                    (0.1, self.go(state, turn_right(action))),
                    (0.1, self.go(state, turn_left(action)))]
        else:
            return [(0.0, state)]
    
    def T(self, state, action):
        return self.transitions[state][action] if action else [(0.0, state)]
 
    def go(self, state, direction):
        """Return the state that results from going in this direction."""

        state1 = vector_add(state, direction)
        return state1 if state1 in self.states else state

    def to_grid(self, mapping):
        """Convert a mapping from (x, y) to v into a [[..., v, ...]] grid."""

        return list(reversed([[mapping.get((x, y), None)
                               for x in range(self.cols)]
                              for y in range(self.rows)]))

    def to_arrows(self, policy):
        chars = {(1, 0): '>', (0, 1): '^', (-1, 0): '<', (0, -1): 'v', None: '.'}
        return self.to_grid({s: chars[a] for (s, a) in policy.items()})


def policy_evaluation(pi, U, mdp, k=20):
    """Return an updated utility mapping U from each state in the MDP to its
    utility, using an approximation (modified policy iteration)."""

    R, T, gamma = mdp.R, mdp.T, mdp.gamma
    for i in range(k):
        for s in mdp.states:
            U[s] = R(s) + gamma*sum(p*U[s1] for (p, s1) in T(s, pi[s]))
    return U

def expected_utility(a, s, U, mdp):
    """The expected utility of doing a in state s, according to the MDP and U."""
    return sum(p*U[s1] for (p, s1) in mdp.T(s, a))

def policy_iteration(mdp):
    """Solve an MDP by policy iteration [Figure 17.7]"""

    U = {s: 0 for s in mdp.states}
    pi = {s: random.choice(mdp.actions(s)) for s in mdp.states}
    reward_list = []
    while True:
        U = policy_evaluation(pi, U, mdp)
        unchanged = True
        for s in mdp.states:
            a = argmax(mdp.actions(s), key=lambda a: expected_utility(a, s, U, mdp))
            reward_list.append(expected_utility(a, s, U, mdp))
            if a != pi[s]:
                pi[s] = a
                unchanged = False
        if unchanged:
            return pi, reward_list
        
def print_table(table, header=None, sep='   ', numfmt='{}'):
    """Print a list of lists as a table, so that columns line up nicely.
    header, if specified, will be printed as the first row.
    numfmt is the format for all numbers; you might want e.g. '{:.2f}'.
    (If you want different formats in different columns,
    don't use print_table.) sep is the separator between columns."""
    justs = ['rjust' if isnumber(x) else 'ljust' for x in table[0]]

    if header:
        table.insert(0, header)

    table = [[numfmt.format(x) if isnumber(x) else x for x in row]
             for row in table]

    sizes = list(
        map(lambda seq: max(map(len, seq)),
            list(zip(*[map(str, row) for row in table]))))

    for row in table:
        print(sep.join(getattr(
            str(x), j)(size) for (j, size, x) in zip(justs, sizes, row)))
        
def isnumber(x):
    """Is x a number?"""
    return hasattr(x, '__int__')


def printPolicyAndExecutionTime(x, env):
    start_time = time.time()
    pi, reward_list = policy_iteration(env)
    execution_time = time.time() - start_time
    #print_table(env.to_arrows(pi))
    avg_reward = sum(reward_list) / len(reward_list)
    print("Execution time for %d iteration: %0.2f seconds and Average reward per iteration is %0.2f"% (x, execution_time, avg_reward))
    return execution_time, avg_reward
        
""" [Figure 17.1]
A 4x3 grid environment that presents the agent with a sequential decision problem.
"""
'''sequential_decision_environment_2_2 = GridMDP([[-0.04, +1],
                                           [-0.04, -1]],
                                          terminals=[(1, 0), (1, 1)])

sequential_decision_environment_4_3 = GridMDP([[-0.04, -0.04, -0.04, +1],
                                           [-0.04, None, -0.04, -1],
                                           [-0.04, -0.04, -0.04, -0.04]],
                                          terminals=[(3, 2), (3, 1)])

sequential_decision_environment_5_5 = GridMDP([[-0.04, -0.04, -0.04, -0.04, -0.04],
                                           [-0.04, None, -0.04, -0.04, -1],
                                           [-0.04, -0.04, None, -0.04, +1],
                                           [-0.04, -0.04, None, -0.04, -0.04],
                                           [None, -0.04, -0.04, -0.04, -0.04]],
                                          terminals=[(4, 2), (4, 3)])'''

def getMdpEnv(x_dim, y_dim, pos_terminal, neg_terminal):
    myEnv = []
    for x in range (x_dim):
        myEnv_y = []
        for y in range (y_dim):
            y_block = random.uniform(0, 1)
            if y_block > 0.9:
                myEnv_y.append(None)
            else:
                myEnv_y.append(-0.04)
        myEnv.append(myEnv_y)
    myEnv[pos_terminal[1]][pos_terminal[0]] = 1
    myEnv[neg_terminal[1]][neg_terminal[0]] = -1
    return GridMDP(myEnv[::-1], terminals=[pos_terminal, neg_terminal])
    
getMdpEnv(5, 5, (4,2), (4,3))
            

printPolicyAndExecutionTime(2, getMdpEnv(2, 2, (1,0), (1,1)))
printPolicyAndExecutionTime(3, getMdpEnv(3, 4, (3,2), (3,1)))
printPolicyAndExecutionTime(5, getMdpEnv(5, 5, (4,2), (4,3)))

print('Collecting data for time tests')
print('-'*75)

execution_time_list = []
iteration_num = []
avg_reward_list = []
for x in range(2, 500, 20):
    iteration_num.append(x)
    execution_time, avg_reward = printPolicyAndExecutionTime(x, getMdpEnv(x, x, (x-1,x-1), (x-1,x-2)))
    execution_time_list.append(execution_time)
    avg_reward_list.append(avg_reward)


import matplotlib.pyplot as plt
plt.plot(iteration_num, execution_time_list)
plt.axis([0, iteration_num[-1], 0, execution_time_list[-1]+1])
plt.xlabel('size of the environment')
plt.ylabel('execution time')
plt.title('MDP execution time vs environment size')
plt.savefig('MDP execution time.png')
plt.show()

plt.plot(iteration_num, avg_reward_list)
plt.axis([0, iteration_num[-1], min(avg_reward_list), max(avg_reward_list)])
plt.xlabel('size of the environment')
plt.ylabel('average reward')
plt.title('MDP average reward vs environment size')
plt.savefig('MDP average reward.png')
plt.show()