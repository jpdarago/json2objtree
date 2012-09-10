#!/usr/bin/python

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

#Arma una asercion dado un texto 
def make_node(assertion_type, text):
	props = {
		'od': make_properties("parallelogram"),
		'ob': make_properties("circle",style="filled",fillcolor="#aacccc"),
		'ad': make_properties("trapezium"),
		'ag': make_properties("hexagon"),
		'dummy': {
			'shape': 'point',
			'filled': 'filled',
			'color': 'black'
		}
	}.get(assertion_type,dict(make_properties("plaintext")))
	return pydot.Node(text, ** props )

Assertion = collections.namedtuple('Asertion',['type','text'])

#Arbol de objetivos
class ObjectiveGraph(object):
	def __init__(self,name):
		self.__name = name 
		self.__graph = pydot.Dot('objetivos', graph_type='digraph')
		self.__node_dict = []

	def get_name(self):
		return self.__name

	name = property(get_name)

	def get_node(self,assertion):
		for node in self.__node_dict:
			if(assertion == node[0]):
				return node[1]
		return None

	def add_node(self,assertion,append=False):
		node = self.get_node(assertion)
		if not node or append:
			node = make_node(*assertion)
			self.__graph.add_node(node)
			self.__node_dict.append((assertion,node))
		return node

	def add_relation_straight(self,child_node,parent_node,properties={}):
		self.__graph.add_edge(pydot.Edge(child_node,parent_node, **properties))

	def add_relation(self,child,parent,properties={}):
		#Agregar ambas aserciones si no estan ya
		child_node = self.add_node(child)
		parent_node = self.add_node(parent)

		#Agregar el eje
		self.add_relation_straight(child_node,parent_node,properties)

	def write(self):
		self.__graph.write_dot(self.name + '.dot')
		self.__graph.write_svg(self.name + '.svg')

dummy_count = 0

def build_tree(data,tree):
	global dummy_count

	#Estamos en un nodo.
	root = Assertion(data['tipo'],data['texto'])
	if 'y-ref' in data.keys():
		dummy_node = tree.add_node(Assertion('dummy',"DUMMY" + str(dummy_count)),append=True)
		dummy_count += 1

		root_node = tree.add_node(root)

		tree.add_relation_straight(dummy_node,root_node)
		for o in data['y-ref']:
			child_node = tree.add_node(Assertion(o['tipo'],o['texto']))
		
			tree.add_relation_straight(child_node,dummy_node, {'arrowhead': 'none'})

			build_tree(o,tree)
	elif 'o-ref' in data.keys():
		for o in data['o-ref']:
			child = Assertion(o['tipo'],o['texto'])
			tree.add_relation(child,root)

			build_tree(o,tree)

	helps = data.get('ayuda',None)
	helps = helps.split(",") if helps else []

	for o in helps:
		soft_obj = Assertion('ob',o)
		tree.add_relation(root,soft_obj, {'label': '++'})

	hardens = data.get('dificulta',"")
	hardens = hardens.split(",") if hardens else []

	for o in hardens:
		soft_obj = Assertion('ob',o)
		tree.add_relation(root,soft_obj, {'label': '--'})

def main():
	if (len(sys.argv) < 2):
		print "Uso: %s [nombre archivo entrada]" 
		sys.exit()

	dummy_count = 0
	with open(sys.argv[1], 'r') as f:
		tree = ObjectiveGraph('objetivos')
		build_tree(json.loads(f.read()), tree)
		tree.write()

if __name__ == '__main__':
	main()