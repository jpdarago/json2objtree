#!/usr/bin/python
#-*- coding: utf-8 -*-

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
import argparse
import textwrap

#Arma las propiedades para hacer el digrafo
def make_properties(shape,style="filled",fillcolor="yellow",extra={}):
	defaults = dict(zip(["shape","style","fillcolor"],[shape,style,fillcolor]))
	
	defaults.update(extra)
	defaults.update({'width': '2.0'})
	return defaults

#Contador de la cantidad de nodos
node_count = 0
#Contador de nodos dummy para los y-refinamientos
dummy_count = 0

#Arma una asercion dado un texto 
def make_node(assertion_type, text):
	"""
		Arma un nodo dado el tipo de asercion y el texto
	"""
	global node_count
	props = {
		'od': make_properties("polygon",extra={'skew': '0.2'}),
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

	w = textwrap.TextWrapper(width=60,break_long_words=False,replace_whitespace=False)

	props['label'] = '\n'.join( w.wrap( text ) )
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
			if assertion == node[0]:
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

	def add_relation(self,child,parent,properties={} ):
		#Agregar ambas aserciones si no estan ya
		child_node = self.add_node(child)
		parent_node = self.add_node(parent)

		#Agregar el eje
		self.add_edge(child_node,parent_node,properties)

	def write(self,extension):
		self.__graph.write(self.name + '.' + extension, None, extension)

def add_impact(tree, root, soft_objs, edge_style):
	"""
		Agrega una arista de impacto sobre objetivo blando entre el nodo root
		y los objetivos en soft_objs, con el estilo indicado
	"""
	for o in soft_objs:
		soft_obj = Assertion('ob',o.strip().capitalize())
		tree.add_relation(root,soft_obj, edge_style)

def build_tree(data,tree):
	"""
		Construye el arbol de objetivos (pasado por parametro como tree), a partir
		del diccionario de datos dict, que tiene forma de json (ver example.json).
	"""
	global dummy_count
	
	node_text = data['texto'].strip().capitalize()
	root = Assertion( data['tipo'], node_text )

	if 'y-ref' in data.keys():
		#El nodo dummy es el circulo negro que se usa para los y-refinamientos
		dummy = Assertion('dummy',"DUMMY" + str(dummy_count))
		dummy_count += 1

		add_dummy_edge = True
		for o in data['y-ref']:
			child = Assertion(o['tipo'],o['texto'])
			t = o['tipo']
			if len(data['y-ref']) == 1 or o['tipo'] == 'ag':
				add_dummy_edge = False
				tree.add_relation(root,child, 
					{'arrowhead': 'none', 'arrowtail': 'none', 'dir': 'both'})
			else:
				tree.add_relation(dummy,child, {'arrowtail': 'none', 'dir': 'back'} )

			build_tree(o,tree)

		if add_dummy_edge:
			tree.add_relation(root,dummy, {'dir': 'back'})

	elif 'o-ref' in data.keys():
		for o in data['o-ref']:
			child = Assertion(o['tipo'],o['texto'].strip().capitalize())
			tree.add_relation(root,child, {'dir': 'back'})

			build_tree(o,tree)

	#Agregar los objetivos blandos que beneficia
	helps = data.get('ayuda',[])
	edge_style = {'label': '++', 'style': 'dotted', 'penwidth': 2}
	add_impact(tree,root,helps,edge_style)

	#Agregar los objetivos blandos que dificulta
	hardens = data.get('dificulta',[])
	edge_style['label'] = '--'
	add_impact(tree,root,hardens,edge_style)

def main():
	#Lee los argumentos de entrada estandar
	parser = argparse.ArgumentParser(description='Dibuja un arbol de objetivos onda Ingenieria I de FCEN UBA a partir de JSON.')

	parser.add_argument('input_file', help=' Archivo con la entrada, - es para entrada estandar ')
	parser.add_argument('-o', dest='output_file', default='--', help=' Archivo de salida. Por default usa SVG y el mismo nombre que la entrada ')

	args = parser.parse_args()

	if args.output_file == '--':
		#Por defecto produce un svg
		name = 'a.svg' if args.input_file == '-' else args.input_file
		args.output_file = os.path.splitext(name)[0] + '.svg'

	output_name, output_extension = os.path.splitext(args.output_file)

	try:
		input_file = sys.stdin if args.input_file == '-' else open(args.input_file,'r')
	except IOError as error:
		print "Error %s: %s" % error

	tree = ObjectiveGraph(output_name)
	data = json.loads( input_file.read() )

	dummy_count = 0 
	node_count = 0
	
	build_tree(data, tree)
	tree.write(output_extension[1:])

if __name__ == '__main__':
	main()