#!/usr/bin/python

#Copyright (c) 2012 -  Juan Pablo Darago
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
#and associated documentation files (the "Software"), to deal in the Software without restriction, 
#including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
#and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
#subject to the following conditions: The above copyright notice and this permission notice shall be 
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
#LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
#IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
#OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import pydot
import json
import collections
import sys
import os.path
import re
import time

#Arma las propiedades para hacer el digrafo
def make_properties(shape,style="filled",fillcolor="yellow"):
	return dict(zip(["shape","style","fillcolor"],[shape,style,fillcolor]))

#Contador de la cantidad de nodos
node_count = 0
#Contador de nodos dummy para los y-refinamientos
dummy_count = 0

#Arma una asercion dado un texto 
def make_node(assertion_type, text):
	global node_count
	props = {
		'od': make_properties("parallelogram"),
		'ob': make_properties("circle",style="filled",fillcolor="#aacccc"),
		'ad': make_properties("trapezium"),
		'ag': make_properties("hexagon"),
		'dummy': {
			'shape': 'point',
			'filled': 'filled',
			'color': 'black',
			'width': '0.1'
		}
	}.get(assertion_type,dict(make_properties("plaintext")))
	props['label'] = text

	node_count += 1
	return pydot.Node(str(node_count), ** props )

class Assertion:
	def __init__(self,type, text):
		self.assertion_type = type
		self.text = text
	
	def __eq__(self,other):
		if isinstance(other,Assertion): 
			return self.assertion_type == other.assertion_type and self.text == other.text
		else:
			return False

#Arbol de objetivos
class ObjectiveGraph(object):
	def __init__(self,name):
		self.__name = name 
		self.__graph = pydot.Dot('objetivos', graph_type='digraph')
		self.__node_list = []

	def get_name(self):
		return self.__name

	name = property(get_name)

	def get_node(self,assertion):
		for node in self.__node_list:
			if(assertion == node[0]):
				return node[1]
		return None

	def add_node(self,assertion):
		node = self.get_node(assertion)
		if not node:
			node = make_node(assertion.assertion_type, assertion.text)
			self.__graph.add_node(node)
			self.__node_list.append((assertion,node))
		return node

	def add_edge(self,child_node,parent_node,properties={}):
		self.__graph.add_edge(pydot.Edge(child_node,parent_node, **properties))

	def add_relation(self,child,parent,properties={}):
		#Agregar ambas aserciones si no estan ya
		child_node = self.add_node(child)
		parent_node = self.add_node(parent)

		#Agregar el eje
		self.add_edge(child_node,parent_node,properties)

	def write(self):
		self.__graph.write_dot(self.name + '.dot')
		self.__graph.write_svg(self.name + '.svg')

def add_impact(tree, root, soft_objs, edge_style):
	for o in soft_objs:
		soft_obj = Assertion('ob',o.strip().capitalize())
		tree.add_relation(root,soft_obj, edge_style)

def build_tree(data,tree):
	global dummy_count
	#Estamos en un nodo.
	root = Assertion(data['tipo'],data['texto'].strip().capitalize())
	if 'y-ref' in data.keys():
		dummy = Assertion('dummy',"DUMMY" + str(dummy_count))
		dummy_count += 1

		is_requirement = False
		for o in data['y-ref']:
			child = Assertion(o['tipo'],o['texto'])
			t = o['tipo']
			if len(data['y-ref']) == 1:
				is_requirement = True #No se puede asignar un agente a algo que no vamos a refinar
				tree.add_relation(root,child, {'arrowhead': 'none', 'arrowtail': 'none', 'dir': 'both'})
			else:
				tree.add_relation(dummy,child, {'arrowtail': 'none', 'dir': 'back'})

			build_tree(o,tree)

		if not is_requirement:
			tree.add_relation(root,dummy, {'dir': 'back'})

	elif 'o-ref' in data.keys():
		for o in data['o-ref']:
			child = Assertion(o['tipo'],o['texto'])
			tree.add_relation(root,child, {'dir': 'back'})

			build_tree(o,tree)


	helps = data.get('ayuda',[])
	edge_style = {'label': '++', 'style': 'dotted', 'penwidth': 2}
	add_impact(tree,root,helps,edge_style)

	hardens = data.get('dificulta',[])
	edge_style['label'] = '--'
	add_impact(tree,root,hardens,edge_style)

def main():
	if (len(sys.argv) < 2):
		print "Uso: %s [nombre archivo entrada]" 
		sys.exit()

	with open(sys.argv[1], 'r') as f:
		tree = ObjectiveGraph('objetivos')
		data = json.loads(f.read())

		dummy_count = node_count = 0
		build_tree(data, tree)

		tree.write()

if __name__ == '__main__':
	main()