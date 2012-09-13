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

import os
import sys
import json
import re
import argparse
import unicodedata

class FormatException(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return "Formato invalido: " + repr(self.value)

separator_tags = ['(',')','[',']','{','}','<','>',':','+','-']

def parse_enclosed(text):
	global separator_tags
	if text[0] in ['"',"'"]:
		#El texto esta quoteado
		for i in range(2,len(text)):
			if text[i] == text[1]:
				if i+1 >= len(text):
					raise FormatException(
						'Terminacion prematura del texto en "%s"' % text[i:])
				elif text[i+1] != ')':
					raise FormatException(
						'Se esperaba ), se obtuvo %s en "%s"' % (text[i+1], text[i:]))

				return text[1:i], text[i+2:]

		raise FormatException(
			'No se encontro %s, posible etiqueta no cerrada en "%s"' % (text[2],text[2:]) )
	else:
		#El texto no esta quoteado
		for i in range(0,len(text)):
			if text[i] == ')':
				return text[:i], text[i+1:]
			elif text[i] in separator_tags:
				raise FormatException(
					'"(" no quoteado contiene caracter %s en "%s" ' % (text[i], text))

		raise FormatException(
			'No se encontro ). posible etiqueta no cerrada en "%s" ' % text[2:] )

def parse_to_json(text):
	""" 
		Parsea la gramatica	a un JSON. Para un ejemplo de la gramatica vease example.jg
	"""
	res = {}
	
	if(len(text) < 2):
		raise FormatException(
			'Terminacion prematura del texto en "%s"' % text)

	assertion_type = text[0:2]
	res['tipo'] = assertion_type

	if(text[2] != '('):
		raise FormatException(
			'Se esperaba ( se obtuvo %s en "%s"' % (text[2], text))

	res['texto'], text = parse_enclosed(text[3:])

	if(len(text) == 0):
		return res, ""

	if(text[0] == '('):
		#Tenemos una etiqueta de reconocimiento de tag
		res['tag'], text = parse_enclosed(text[1:])

	if(text[0] in ["{","["]):
		#Tenemos un y-refinamiento o un o-refinamiento

		open_tag = text[0]
		close_tag = '}' if text[0] == '{' else ']'
		dict_key = 'y-ref' if text[0] == '{' else 'o-ref'

		res[dict_key] = []
		while(True):
			child, rem_text = parse_to_json(text[1:])

			res[dict_key].append(child)
			text = rem_text

			#Sacar la coma de la lista si hay
			if(text[0] != ','): 
				break
		if(text[0] != close_tag):
			raise FormatException(
				'Se esperaba %s como cierre del refinamiento en "%s" >' % (close_tag,text) )
		text = text[1:]

	if(len(text) == 0):
		return res, ""

	if text[0] == '<':
		#Tenemos lista de impacto en objetivos blandos y duros
		res['ayuda'] =  []
		res['dificulta'] = []
		
		s = "__INVALID__"
		for i in range(0,len(text)):
			if(text[i] == '>'):
				s = text[1:i]
				text = text[i+1:]
				break

		if s == "__INVALID__":
			raise FormatException(
				"Lista de efectos en objetivo blando incompleta en < %s >" % text)

		for elem in s.split(","):
			if not ':' in elem:
				raise FormatException(
					"Lista de objetivos blandos afectados en < %s >" % text)

			impc,obj = elem.split(':')
			if(impc[0] == '+'):
				res['ayuda'].append(obj)
			else:
				res['dificulta'].append(obj)

	return res, text

def parse_to_jg(tree, indentation=""):
	"""
		Parsea el arbol en diccionario de python, tomado de un JSON, a un coso de gramatica JG
	"""
	str_res = indentation + tree['tipo'] + "('" + tree['texto'] + "')"

	if 'y-ref' in tree.keys() or 'o-reg' in tree.keys():
		sep_start,sep_end = ('{','}') if 'y-ref' in tree.keys() else ('[', ']')
		
		refinements = tree.get('y-ref',None) or tree.get('o-ref',[])
		parse_subtree = lambda t: parse_to_jg(t,indentation+'\t')
		subtrees_text = ",\n".join(map(parse_subtree, refinements))

		str_res += sep_start + "\n" + subtrees_text + "\n" + indentation + sep_end

	ayudas = [('+',s) for s in tree.get('ayuda',[])]
	dificultas = [('-',s) for s in tree.get('dificulta',[])]

	if( len(ayudas) + len(dificultas) > 0):
		impact_text = ",".join(map(lambda s: "%s:%s" % s),ayudas+dificultas)
		str_res += '<' + impact_text + '>'

	return str_res

def cleanup(text):
	""" 
		Borrarle todos los espacios entre los separadores de la gramatica
	"""
	text = re.sub(r"#(.*)\n","",text) #Borrarle los comentarios
	text = re.sub(r"^\s*$","",text) #Borrar lineas vacias
	
	#Borrar los espacios entre los separadores, para poder parsear mas facil
	global separtor_tags
	separators = "".join(map(lambda x : re.escape(x), separator_tags))
	#El \S{,2} es un hack choto para que borre los costados izquierdos de las aserciones, en teoria anda
	#pero sospechar mucho MUCHO de el :D
	regex = re.compile("\s*(\S{,2}[" + separators + "])\s*")
	return re.sub(regex,lambda m: m.group(1), text)

def main():
	parser = argparse.ArgumentParser(description='Parsea la gramatica de arboles que definimos a JSON.')

	parser.add_argument('-i', dest='input_file', default='-', 
		help=' Archivo con la entrada. Si no se especifica se toma entrada estandar ')
	parser.add_argument('-o', dest='output_file', default='--', 
		help=' Archivo de salida. Si no se especifica se toma salida estandar ')
	parser.add_argument('-c', dest='only_cleaned',action='store_true',default=False,
		help=" Imprimir unicamente el archivo original pero limpiado por el parser")
	parser.add_argument('-r', dest='to_json', action='store_false', default=True,
		help=" Pasar de JSON a gramatica, no al reves. Invalida -c "
	)
	args = parser.parse_args()

	try:
		input_file = sys.stdin if args.input_file == '-' else open(args.input_file,'r')
	except IOError, error:
		print "Error %s: %s" % (error.errno, os.strerror(error.errno))
		exit()

	try:
		output_file = sys.stdout if args.output_file == '--' else open(args.output_file,'w')
	except IOError, error:
		print "Error %s: %s" % (error.errno, os.strerror(error.errno))
		exit()

	if args.to_json:
		cleaned = cleanup ( input_file.read() )

		if args.only_cleaned:
			print cleaned
		else:
			try:
				data,rem = parse_to_json( cleanup( cleaned ) )
			except FormatException as error:
				print error
				exit()
		output_file.write( unicode( json.dumps(data, sort_keys=True, indent=4) ).encode('utf-8') )
	else:
		output_file.write( unicode(parse_to_jg( json.loads( input_file.read() ) ) ).encode('utf-8') )

if __name__ == "__main__":
	main()
