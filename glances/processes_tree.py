# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import collections

from glances.compat import iteritems

import psutil


class ProcessTreeNode(object):

    """Represent a process tree.

    We avoid recursive algorithm to manipulate the tree because function
    calls are expensive with CPython.
    """

    def __init__(self, process=None, stats=None, sort_key=None, sort_reverse=True, root=False):
        self.process = process
        self.stats = stats
        self.children = []
        self.children_sorted = False
        self.sort_key = sort_key
        self.sort_reverse = sort_reverse
        self.is_root = root

    def __str__(self):
        """Return the tree as a string for debugging."""
        lines = []
        nodes_to_print = collections.deque([collections.deque([("#", self)])])
        while nodes_to_print:
            indent_str, current_node = nodes_to_print[-1].pop()
            if not nodes_to_print[-1]:
                nodes_to_print.pop()
            if current_node.is_root:
                lines.append(indent_str)
            else:
                lines.append("%s[%s]" %
                             (indent_str, current_node.process.name()))
            indent_str = " " * (len(lines[-1]) - 1)
            children_nodes_to_print = collections.deque()
            for child in current_node.children:
                if child is current_node.children[-1]:
                    tree_char = "└─"
                else:
                    tree_char = "├─"
                children_nodes_to_print.appendleft(
                    (indent_str + tree_char, child))
            if children_nodes_to_print:
                nodes_to_print.append(children_nodes_to_print)
        return "\n".join(lines)

    def set_sorting(self, key, reverse):
        """Set sorting key or func for use with __iter__.

        This affects the whole tree from this node.
        """
        if self.sort_key != key or self.sort_reverse != reverse:
            nodes_to_flag_unsorted = collections.deque([self])
            while nodes_to_flag_unsorted:
                current_node = nodes_to_flag_unsorted.pop()
                current_node.children_sorted = False
                current_node.sort_key = key
                current_node.reverse_sorting = reverse
                nodes_to_flag_unsorted.extend(current_node.children)

    def get_weight(self):
        """Return 'weight' of a process and all its children for sorting."""
        if self.sort_key == 'name' or self.sort_key == 'username':
            return self.stats[self.sort_key]

        # sum ressource usage for self and children
        total = 0
        nodes_to_sum = collections.deque([self])
        while nodes_to_sum:
            current_node = nodes_to_sum.pop()
            if isinstance(self.sort_key, collections.Callable):
                total += self.sort_key(current_node.stats)
            elif self.sort_key == "io_counters":
                stats = current_node.stats[self.sort_key]
                total += stats[0] - stats[2] + stats[1] - stats[3]
            elif self.sort_key == "cpu_times":
                total += sum(current_node.stats[self.sort_key])
            else:
                total += current_node.stats[self.sort_key]
            nodes_to_sum.extend(current_node.children)

        return total

    def __len__(self):
        """Return the number of nodes in the tree."""
        total = 0
        nodes_to_sum = collections.deque([self])
        while nodes_to_sum:
            current_node = nodes_to_sum.pop()
            if not current_node.is_root:
                total += 1
            nodes_to_sum.extend(current_node.children)
        return total

    def __iter__(self):
        """Iterator returning ProcessTreeNode in sorted order, recursively."""
        if not self.is_root:
            yield self
        if not self.children_sorted:
            # optimization to avoid sorting twice (once when limiting the maximum processes to grab stats for,
            # and once before displaying)
            self.children.sort(
                key=self.__class__.get_weight, reverse=self.sort_reverse)
            self.children_sorted = True
        for child in self.children:
            for n in iter(child):
                yield n

    def iter_children(self, exclude_incomplete_stats=True):
        """Iterator returning ProcessTreeNode in sorted order.

        Return only children of this node, non recursive.

        If exclude_incomplete_stats is True, exclude processes not
        having full statistics. It can happen after a resort (change of
        sort key) because process stats are not grabbed immediately, but
        only at next full update.
        """
        if not self.children_sorted:
            # optimization to avoid sorting twice (once when limiting the maximum processes to grab stats for,
            # and once before displaying)
            self.children.sort(
                key=self.__class__.get_weight, reverse=self.sort_reverse)
            self.children_sorted = True
        for child in self.children:
            if not exclude_incomplete_stats or "time_since_update" in child.stats:
                yield child

    def find_process(self, process):
        """Search in tree for the ProcessTreeNode owning process.

        Return it or None if not found.
        """
        nodes_to_search = collections.deque([self])
        while nodes_to_search:
            current_node = nodes_to_search.pop()
            if not current_node.is_root and current_node.process.pid == process.pid:
                return current_node
            nodes_to_search.extend(current_node.children)

    @staticmethod
    def build_tree(process_dict, sort_key, sort_reverse, hide_kernel_threads, excluded_processes):
        """Build a process tree using using parent/child relationships.

        Return the tree root node.
        """
        tree_root = ProcessTreeNode(root=True)
        nodes_to_add_last = collections.deque()

        # first pass: add nodes whose parent are in the tree
        for process, stats in iteritems(process_dict):
            new_node = ProcessTreeNode(process, stats, sort_key, sort_reverse)
            try:
                parent_process = process.parent()
            except psutil.NoSuchProcess:
                # parent is dead, consider no parent
                parent_process = None
            if (parent_process is None) or (parent_process in excluded_processes):
                # no parent, or excluded parent, add this node at the top level
                tree_root.children.append(new_node)
            else:
                parent_node = tree_root.find_process(parent_process)
                if parent_node is not None:
                    # parent is already in the tree, add a new child
                    parent_node.children.append(new_node)
                else:
                    # parent is not in tree, add this node later
                    nodes_to_add_last.append(new_node)

        # next pass(es): add nodes to their parents if it could not be done in
        # previous pass
        while nodes_to_add_last:
            # pop from left and append to right to avoid infinite loop
            node_to_add = nodes_to_add_last.popleft()
            try:
                parent_process = node_to_add.process.parent()
            except psutil.NoSuchProcess:
                # parent is dead, consider no parent, add this node at the top
                # level
                tree_root.children.append(node_to_add)
            else:
                if (parent_process is None) or (parent_process in excluded_processes):
                    # no parent, or excluded parent, add this node at the top level
                    tree_root.children.append(node_to_add)
                else:
                    parent_node = tree_root.find_process(parent_process)
                    if parent_node is not None:
                        # parent is already in the tree, add a new child
                        parent_node.children.append(node_to_add)
                    else:
                        # parent is not in tree, add this node later
                        nodes_to_add_last.append(node_to_add)

        return tree_root
