from abc import *
import math

import numpy as np

from networks.abstracts import BaseNetwork
from networks.neat.genes import Genome


class NeatFeedForward(BaseNetwork):
    def __init__(self, num_state, num_action, discrete_action):
        self.num_state = num_state
        self.num_action = num_action
        self.discrete_action = discrete_action

        self.genome = Genome(num_state, num_action)
        self.model = FeedForwardNetwork.create(self.genome)

    def forward(self, x):
        output = self.model.activate(x[0])
        return np.array(output)

    def zero_init(self):
        pass

    def normal_init(self, mu, std):
        self.genome = Genome(self.num_state, self.num_action, mu, std)
        self.model = FeedForwardNetwork.create(self.genome)

    def reset(self):
        pass

    def get_param_list(self):
        pass

    def apply_param(self, param_lst: list):
        pass


class FeedForwardNetwork(object):
    def __init__(self, inputs, outputs, node_evals):
        self.input_nodes = inputs
        self.output_nodes = outputs
        self.node_evals = node_evals
        self.values = dict((key, 0.0) for key in inputs + outputs)

    def activate(self, inputs):
        if len(self.input_nodes) != len(inputs):
            raise RuntimeError("Expected {0:n} inputs, got {1:n}".format(len(self.input_nodes), len(inputs)))

        for k, v in zip(self.input_nodes, inputs):
            self.values[k] = v

        for node, act_func, bias, links in self.node_evals:
            node_inputs = []
            for i, w in links:
                node_inputs.append(self.values[i] * w)
            self.values[node] = act_func(bias + sum(node_inputs))

        return [self.values[i] for i in self.output_nodes]

    @staticmethod
    def create(genome):
        """Receives a genome and returns its phenotype (a FeedForwardNetwork)."""

        # Gather expressed connections.
        connections = [cg.connection for cg in genome.connections.values() if cg.enabled]
        sensor_nodes = genome.node_genes.get_sensor_nodes()
        output_nodes = genome.node_genes.get_output_nodes()
        layers = feed_forward_layers(sensor_nodes, output_nodes, connections)
        node_evals = []
        for layer in layers:
            for node in layer:
                inputs = []
                node_expr = []  # currently unused
                for conn_key in connections:
                    inode, onode = conn_key
                    if onode == node:
                        cg = genome.connections[conn_key]
                        inputs.append((inode, cg.weight))
                        node_expr.append("v[{}] * {:.7e}".format(inode, cg.weight))

                ng = genome.nodes[node]
                activation_function = math.tanh
                node_evals.append((node, activation_function, ng.bias, inputs))

        return FeedForwardNetwork(sensor_nodes, output_nodes, node_evals)


def required_for_output(inputs, outputs, connections):
    """
    Collect the nodes whose state is required to compute the final network output(s).
    :param inputs: list of the input identifiers
    :param outputs: list of the output node identifiers
    :param connections: list of (input, output) connections in the network.
    NOTE: It is assumed that the input identifier set and the node identifier set are disjoint.
    By convention, the output node ids are always the same as the output index.

    Returns a set of identifiers of required nodes.
    """

    required = set(outputs)
    s = set(outputs)
    while 1:
        # Find nodes not in S whose output is consumed by a node in s.
        t = set(a for (a, b) in connections if b in s and a not in s)

        if not t:
            break

        layer_nodes = set(x for x in t if x not in inputs)
        if not layer_nodes:
            break

        required = required.union(layer_nodes)
        s = s.union(t)

    return required


def feed_forward_layers(inputs, outputs, connections):
    """
    Collect the layers whose members can be evaluated in parallel in a feed-forward network.
    :param inputs: list of the network input nodes
    :param outputs: list of the output node identifiers
    :param connections: list of (input, output) connections in the network.

    Returns a list of layers, with each layer consisting of a set of node identifiers.
    Note that the returned layers do not contain nodes whose output is ultimately
    never used to compute the final network output.
    """

    required = required_for_output(inputs, outputs, connections)

    layers = []
    s = set(inputs)
    while 1:
        # Find candidate nodes c for the next layer.  These nodes should connect
        # a node in s to a node not in s.
        c = set(b for (a, b) in connections if a in s and b not in s)
        # Keep only the used nodes whose entire input set is contained in s.
        t = set()
        for n in c:
            if n in required and all(a in s for (a, b) in connections if b == n):
                t.add(n)

        if not t:
            break

        layers.append(t)
        s = s.union(t)

    return layers
