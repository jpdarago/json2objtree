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

#Devuelve la longitud del texto para graficar
def text_width(lines,factor):
	max_len = max( map( len, lines ) )
	return max_len / factor #6.5

#Devuelve la altura del texto para graficar
def text_height(lines, factor):
	return len(lines) / factor #1.4

#Arma una asercion dado un texto 
def make_node(assertion_type, text):
	"""
		Arma un nodo dado el tipo de asercion y el texto
	"""
	global node_count

	w = textwrap.TextWrapper(
		width=50,break_long_words=False,replace_whitespace=False)

	factors = {
		'od': (7.0,1.7),
		'ob': (8.1,1.7),
		'ad': (7.2,1.6),
		'ag': (4.1,1.2)
	}

	text_props = {}
	if assertion_type != 'dummy':
		text = w.wrap(text)
		text_props = {
			'fixedsize': True,
			'label': '\n'.join(text),
			'width': text_width(text,factors[assertion_type][0]),
			'height': text_height(text,factors[assertion_type][1]),
		}

	if assertion_type == 'od':
		text_props['skew'] = '0.05'

	props = {
		'od': make_properties("parallelogram",extra=text_props),
		'ob': make_properties("circle",style="filled",fillcolor="#aacccc",extra=text_props),
		'ad': make_properties("trapezium",extra=text_props),
		'ag': make_properties("hexagon",extra=text_props),
		'dummy': {
			'shape': 'point',
			'filled': 'filled',
			'color': 'black',
			'width': '0.1'
		}
	}.get(assertion_type,dict(make_properties("plaintext")))
	
	node_count += 1
	return pydot.Node(str(node_count), ** props )

class Assertion:
	def __init__(self,type, text, tag=None):
		self.assertion_type = type
		self.text = text.strip()
		self.tag = None
	def __eq__(self,other):
		if isinstance(other,Assertion): 
			same_type = self.assertion_type == other.assertion_type
			same_text = self.text == other.text 

			return same_type and same_text
		else:
			return False

#Arbol de objetivos
class ObjectiveGraph(object):
	def __init__(self):
		self.__graph = pydot.Dot('objetivos', graph_type='digraph')
		self.__graph.set_aspect('3')
		self.__nodes = []
		self.__assertions = []

	def add_node(self,assertion,add_to_tree=True):
		if assertion.assertion_type != 'tg':
			node = make_node(assertion.assertion_type, assertion.text)

			self.__assertions.append(assertion)
			self.__nodes.append(node)

			if add_to_tree:
				self.__graph.add_node(node)

			return len(self.__nodes) - 1
		else:
			for i,a in enumerate(self.__assertions):
				if a.tag == assertion.text:
					return i
			return -1

	def add_relation(self,child_index,parent_index,properties={},found_branch=True):
		if not found_branch:
			return

		if child_index < 0 or child_index >= len(self.__nodes):
			raise Exception('Hijo invalido: %s' % child_index)

		if parent_index < 0 or parent_index >= len(self.__nodes):
			raise Exception('Padre invalido: %s' % parent_index)

		#Agregar el eje
		self.__graph.add_edge(
			pydot.Edge(
				self.__nodes[child_index],
				self.__nodes[parent_index], 
				**properties))

	def write(self,output_file):
		output_name, output_extension = os.path.splitext(output_file)
		self.__graph.write(output_file, None, output_extension[1:])

def build_assertion(data):
	return Assertion( data['tipo'], data['texto'], data.get('tag',None))

def add_impact(tree, root_index, soft_objs, edge_style,should_add):
	"""
		Agrega una arista de impacto sobre objetivo blando entre el nodo root
		y los objetivos en soft_objs, con el estilo indicado
	"""
	for o in soft_objs:
		soft_obj_index = tree.add_node( Assertion('ob',o), should_add )
		tree.add_relation(root_index,soft_obj_index, edge_style, should_add )

def build_tree(data, branch):
	node_count = 0

	tree = ObjectiveGraph()
	root = build_assertion( data )

	add_all = branch == '__all'
	is_branch = data.get('tag','__none') == branch 
	found_branch = add_all or is_branch

	build_branches(data,tree,tree.add_node(root,found_branch),branch,found_branch)
	return tree

def build_branches(data,tree,root_index,branch,found_branch):
	"""
		Construye el arbol de objetivos (pasado por parametro como tree), a partir
		del diccionario de datos dict, que tiene forma de json (ver example.json).
	"""
	global dummy_count

	if 'y-ref' in data.keys():
		#El nodo dummy es el circulo negro que se usa para los y-refinamientos
		dummy_index = -1
		
		for o in data['y-ref']: 
			is_branch = o.get('tag','__none') == branch
			has_found_branch = found_branch or is_branch

			child_index = tree.add_node(build_assertion(o),has_found_branch)

			if len(data['y-ref']) == 1 or o['tipo'] == 'ag':
				tree.add_relation(root_index,child_index, 
					{'arrowhead': 'none', 'arrowtail': 'none', 'dir': 'both'},has_found_branch)
			else:
				if dummy_index == -1:
					dummy = Assertion('dummy',"DUMMY")
					dummy_index = tree.add_node(dummy,found_branch)

				tree.add_relation(dummy_index,child_index, 
					{'arrowtail': 'none', 'dir': 'back'}, found_branch )

			build_branches(o,tree,child_index, branch, has_found_branch)

		if dummy_index != -1:
			tree.add_relation(root_index,dummy_index, {'dir': 'back'}, has_found_branch)

	elif 'o-ref' in data.keys():
		for o in data['o-ref']:
			is_branch = o.get('tag','__none') == branch
			has_found_branch = found_branch or is_branch

			child_index = tree.add_node(build_assertion(o),has_found_branch)
			tree.add_relation(root_index,child_index, {'dir': 'back'},has_found_branch)

			build_branches(o,tree,child_index,branch,has_found_branch)

	#Agregar los objetivos blandos que beneficia
	helps = data.get('ayuda',[])
	edge_style = {'label': '++', 'style': 'dotted', 'penwidth': 2}
	add_impact(tree,root_index,helps,edge_style,found_branch)

	#Agregar los objetivos blandos que dificulta
	hardens = data.get('dificulta',[])
	edge_style['label'] = '--'
	add_impact(tree,root_index,hardens,edge_style,found_branch)

def main():
	#Lee los argumentos de entrada estandar
	parser = argparse.ArgumentParser(
		description='Dibuja un arbol de objetivos onda Ingenieria I de FCEN UBA a partir de JSON.')

	parser.add_argument('-i',dest='input_file', default='--', 
		help=' Archivo con la entrada. Si se ignora es entrada estandar ')
	parser.add_argument('-o', dest='output_file', default='--', 
		help=" Archivo de salida. "
		+ "Por default usa SVG y el mismo nombre que la entrada,"
		+ " o draw.svg si se leyo de stdin" )
	parser.add_argument('-r',dest='branch', default='__all', 
		help=' Tag de la rama que queremos graficar esta vez.')

	args = parser.parse_args()

	if args.output_file == '--':
		#Por defecto produce un svg
		name = 'draw.svg' if args.input_file == '-' else args.input_file
		args.output_file = os.path.splitext(name)[0] + '.svg'

	try:
		input_file = sys.stdin if args.input_file == '--' else open(args.input_file,'r')
	except IOError as error:
		print "Error %s: %s" % error

	data = json.loads( input_file.read() )
	
	build_tree(data,args.branch).write(args.output_file)

if __name__ == '__main__':
	main()