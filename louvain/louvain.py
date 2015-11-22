#!/usr/bin/env python3
# coding: utf-8

import copy
import networkx as nx

from itertools import permutations
from itertools import combinations
from collections import defaultdict

class Louvain(object):
    
    @classmethod
    def convertIGraphToNxGraph(cls, igraph):
        node_names = igraph.vs["names"]
        edge_list = igraph.get_edgelist()
        weight_list = igraph.es["weight"]
        node_dict = defaultdict(str)

        for idx, node in enumerate(igraph.vs):
            node_dict[node.index] = node_names[idx]

        convert_list = []
        for idx in range(len(edge_list)):
            edge = edge_list[idx]
            new_edge = (node_dict[edge[0]], node_dict[edge[1]], weight_list)
            convert_list.append(new_edge)

        convert_graph = nx.Graph()
        convert_graph.add_weighted_edges_from(convert_list)
        return convert_graph

    @classmethod
    def getBestPartition(cls, graph):
        node2com, edge_weights = cls._setNode2Com(graph)

        node2com = cls._runFirstPhase(node2com, edge_weights)
        best_modularity = cls.computeModularity(node2com, edge_weights)

        partition = copy.deepcopy(node2com)
        new_node2com, new_edge_weights = cls._runSecondPhase(node2com, edge_weights)

        while True:
            new_node2com = cls._runFirstPhase(new_node2com, new_edge_weights)
            modularity = cls.computeModularity(new_node2com, new_edge_weights)
            if best_modularity == modularity:
                break
            best_modularity = modularity
            partition = cls._updatePartition(new_node2com, partition)
            _new_node2com, _new_edge_weights = cls._runSecondPhase(new_node2com, new_edge_weights)
            new_node2com = _new_node2com
            new_edge_weights = _new_edge_weights
        return partition

    @classmethod
    def computeModularity(cls, node2com, edge_weights):
        q = 0
        all_edge_weights = sum([weight for start in edge_weights.keys() for end, weight in edge_weights[start].items()]) / 2

        com2node = defaultdict(list)
        for node, com_id in node2com.items():
            com2node[com_id].append(node)

        for com_id, nodes in com2node.items():
            node_combinations = list(combinations(nodes, 2)) + [(node, node) for node in nodes]
            cluster_weight = 0.
            for node_pair in node_combinations:
                cluster_weight += edge_weights[node_pair[0]][node_pair[1]]
            tot = cls.getDegreeOfCluster(nodes, node2com, edge_weights)
            q += (cluster_weight / (2 * all_edge_weights)) - (tot / (2 * all_edge_weights)) ** 2
        return q

    @classmethod
    def getDegreeOfCluster(cls, nodes, node2com, edge_weights):
        weight = sum([sum(list(edge_weights[n].values())) for n in nodes])
        return weight

    @classmethod
    def _updatePartition(cls, new_node2com, partition):
        # new_node2com : {'古いcom_id' : "新しいcom_id"}
        reverse_partition = defaultdict(list)
        for node, com_id in partition.items():
            reverse_partition[com_id].append(node)

        for old_com_id, new_com_id in new_node2com.items():
            for old_com in reverse_partition[old_com_id]:
                partition[old_com] = new_com_id
        return partition

    @classmethod
    def _runFirstPhase(cls, node2com, edge_weights):
        all_edge_weights = sum([weight for start in edge_weights.keys() for end, weight in edge_weights[start].items()]) / 2
        status = True
        while status:
            statuses = []
            for node in list(node2com.keys()):
                statuses = []
                com_id = node2com[node]
                neigh_nodes = sorted([edge[0] for edge in cls.getNeighborNodes(node, edge_weights)])

                max_delta = 0.
                max_com_id = com_id
                communities = {}
                for neigh_node in sorted(neigh_nodes):
                    node2com_copy = copy.deepcopy(node2com)
                    if node2com_copy[neigh_node] in communities:
                        continue
                    communities[node2com_copy[neigh_node]] = 1
                    node2com_copy[node] = node2com_copy[neigh_node]

                    delta_q = 2 * cls.getNodeWeightInCluster(node, node2com_copy, edge_weights) - cls.getTotWeight(node, node2com_copy, edge_weights) * cls.getNodeWeights(node, edge_weights) / all_edge_weights
                    if delta_q > max_delta:
                        max_delta = delta_q
                        max_com_id = node2com_copy[neigh_node]

                node2com[node] = max_com_id
                statuses.append(com_id != max_com_id)

            if sum(statuses) == 0:
                break

        return node2com

    @classmethod
    def _runSecondPhase(cls, node2com, edge_weights):
        com2node = defaultdict(list)

        new_node2com = {}
        new_edge_weights = defaultdict(lambda : defaultdict(float))

        for node, com_id in node2com.items():
            com2node[com_id].append(node)
            if com_id not in new_node2com:
                new_node2com[com_id] = com_id

        nodes = list(node2com.keys())
        node_pairs = list(permutations(nodes, 2)) + [(node, node) for node in nodes]
        for edge in node_pairs:
            new_edge_weights[new_node2com[node2com[edge[0]]]][new_node2com[node2com[edge[1]]]] += edge_weights[edge[0]][edge[1]]
        return new_node2com, new_edge_weights

    @classmethod
    def getTotWeight(cls, node, node2com, edge_weights):
        nodes = []
        for n, com_id in node2com.items():
            if com_id == node2com[node] and node != n:
                nodes.append(n)

        weight = 0.
        for n in nodes:
            weight += sum(list(edge_weights[n].values()))
        return weight

    @classmethod
    def getNeighborNodes(cls, node, edge_weights):
        if node not in edge_weights:
            return 0
        return list(edge_weights[node].items())

    @classmethod
    def getNodeWeightInCluster(cls, node, node2com, edge_weights):
        neigh_nodes = cls.getNeighborNodes(node, edge_weights)
        node_com = node2com[node]
        weights = 0.
        for neigh_node in neigh_nodes:
            if node_com == node2com[neigh_node[0]]:
                weights += neigh_node[1]

        return weights
    
    @classmethod
    def getNodeWeights(cls, node, edge_weights):
        return sum([weight for weight in edge_weights[node].values()])

    @classmethod
    def _setNode2Com(cls, graph):
        # initialize 
        node2com = {}
        edge_weights = defaultdict(lambda : defaultdict(float))
        for idx, node in enumerate(graph.nodes()):
            node2com[node] = idx
            for edge in graph[node].items():
                edge_weights[node][edge[0]] = edge[1]["weight"]

        return node2com, edge_weights
