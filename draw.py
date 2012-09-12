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
	return defaults

#Contador de la cantidad de nodos
node_count = 0

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

	w = textwrap.TextWrapper(width=50,break_long_words=False,replace_whitespace=False)

	props['label'] = '\n'.join( w.wrap( text ) )
	node_count += 1
	return pydot.Node(str(node_count), ** props )

class Assertion:
	def __init__(self,type, text):
		self.assertion_type = type
		self.text = text.strip().capitalize()
	
	def __eq__(self,other):
		if isinstance(other,Assertion): 
			return self.assertion_type == other.assertion_type and self.text == other.text
		else:
			return False

#Arbol de objetivos
class ObjectiveGraph(object):
	def __init__(self):
		self.__graph = pydot.Dot('objetivos', graph_type='digraph')
		self.__nodes = []

	def add_node(self,assertion):
		node = make_node(assertion.assertion_type, assertion.text)

		self.__graph.add_node(node)
		self.__nodes.append(node)

		return len(self.__nodes) - 1

	def add_relation(self,child_index,parent_index,properties={} ):
		if child_index < 0 or child_index >= len(self.__nodes):
			raise Exception('Hijo invalido: %s' % child_index)

		if parent_index < 0 or parent_index >= len(self.__nodes):
			raise Exception('Padre invalido: %s' % root_index)

		#Agregar el eje
		self.__graph.add_edge(pydot.Edge(self.__nodes[child_index],self.__nodes[parent_index], **properties))

	def write(self,output_file):
		output_name, output_extension = os.path.splitext(output_file)
		self.__graph.write(output_file, None, output_extension[1:])

def add_impact(tree, root_index, soft_objs, edge_style):
	"""
		Agrega una arista de impacto sobre objetivo blando entre el nodo root
		y los objetivos en soft_objs, con el estilo indicado
	"""
	for o in soft_objs:
		soft_obj_index = tree.add_node( Assertion('ob',o) )
		tree.add_relation(root_index,soft_obj_index, edge_style)

def build_tree(data):
	node_count = 0

	tree = ObjectiveGraph()
	root = Assertion( data['tipo'], data['texto'] )

	build_branches(data,tree,tree.add_node(root))
	return tree

def build_branches(data,tree,root_index):
	"""
		Construye el arbol de objetivos (pasado por parametro como tree), a partir
		del diccionario de datos dict, que tiene forma de json (ver example.json).
	"""
	global dummy_count

	if 'y-ref' in data.keys():
		#El nodo dummy es el circulo negro que se usa para los y-refinamientos
		dummy_index = -1
		
		for o in data['y-ref']: 
			child_index = tree.add_node(Assertion(o['tipo'],o['texto']))

			if len(data['y-ref']) == 1 or o['tipo'] == 'ag':
				tree.add_relation(root_index,child_index, 
					{'arrowhead': 'none', 'arrowtail': 'none', 'dir': 'both'})
			else:
				if dummy_index == -1:
					dummy = Assertion('dummy',"DUMMY")
					dummy_index = tree.add_node(dummy)

				tree.add_relation(dummy_index,child_index, 
					{'arrowtail': 'none', 'dir': 'back'} )

			build_branches(o,tree,child_index)

		if dummy_index != -1:
			tree.add_relation(root_index,dummy_index, {'dir': 'back'})

	elif 'o-ref' in data.keys():
		for o in data['o-ref']:
			child_index = tree.add_node(Assertion(o['tipo'],o['texto']))
			tree.add_relation(root_index,child_index, {'dir': 'back'})

			build_branches(o,tree,child_index)

	#Agregar los objetivos blandos que beneficia
	helps = data.get('ayuda',[])
	edge_style = {'label': '++', 'style': 'dotted', 'penwidth': 2}
	add_impact(tree,root_index,helps,edge_style)

	#Agregar los objetivos blandos que dificulta
	hardens = data.get('dificulta',[])
	edge_style['label'] = '--'
	add_impact(tree,root_index,hardens,edge_style)

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

	try:
		input_file = sys.stdin if args.input_file == '-' else open(args.input_file,'r')
	except IOError as error:
		print "Error %s: %s" % error

	data = json.loads( input_file.read() )
	
	build_tree(data).write(args.output_file)

if __name__ == '__main__':
	main()