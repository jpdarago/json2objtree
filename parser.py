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

import os
import sys
import json
import re
import argparse

class FormatException(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return "Formato invalido: " + repr(self.value)

def parse(text):
	""" 
		Parsea la gramatica	a un JSON. Para un ejemplo vease example.jg
	"""
	res = {}

	if(len(text) < 2):
		raise FormatException('Terminacion prematura del texto en < %s >' % text)

	assertion_type = text[0:2]
	res['tipo'] = assertion_type

	if(text[2] != '('):
		raise FormatException('Se esperaba ( se obtuvo %s en < %s >' % (text[2], text[:min(2,len(text))]))

	label_end = 0
	if text[2] in ['"',"'"]:
		#El texto esta quoteado quoteado
		for i in range(3,len(text)):
			if text[i] == text[2]:
				res['texto'] = text[4:i] 
				if i+1 >= len(text):
					raise FormatException('Terminacion prematura del texto en < %s >' % text[i:])
				elif text[i] != ')':
					raise FormatException('Se esperaba ) se obtuvo %s en < %s >' % (text[i+1], text[i:]))

				label_end = i+2
				break

		if label_end == -1:
			raise FormatException('No se encontro %s, posible label de objetivo no cerrada en < %s >' % (text[2],text[2:]) )
	else:
		#El texto no esta quoteado
		for i in range(2,len(text)):
			if text[i] == ')':
				res['texto'] = text[3:i] 
				label_end = i+1
				break

		if label_end == -1:
			raise FormatException('No se encontro ). posible label de objetivo no cerrada en < %s >' % text[2:] )

	text = text[label_end:]

	if(len(text) == 0):
		return res, ""

	if(text[0] in ["{","["]):
		open_tag = text[0]
		close_tag = '}' if text[0] == '{' else ']'
		dict_key = 'y-ref' if text[0] == '{' else 'o-ref'

		res[dict_key] = []
		while(True):
			child, rem_text = parse(text[1:])

			res[dict_key].append(child)
			text = rem_text

			#Sacar la coma de la lista si hay
			if(text[0] != ','): 
				break
		if(text[0] != close_tag):
			raise FormatException('Se esperaba cierre del refinamiento en < %s >' % text)
		text = text[1:]

	if(len(text) == 0):
		return res, ""

	if text[0] == '<':
		close_tag = '>'
		
		res['ayuda'] =  []
		res['dificulta'] = []
		
		s = "__INVALID__"
		for i in range(0,len(text)):
			if(text[i] == '>'):
				s = text[1:i]
				text = text[i+1:]
				break

		if s == "__INVALID__":
			raise FormatException("Lista de efectos en objetivo blando incompleta en < %s >" % text)

		for elem in s.split(","):
			impc,obj = elem.split(':')
			if(impc[0] == '+'):
				res['ayuda'].append(obj)
			else:
				res['dificulta'].append(obj)

	return res, text

def cleanup(text):
	""" 
		Borrarle todos los espacios entre los separadores de la gramatica
	"""
	text = re.sub(r"#(.*)\n","",text) #Borrarle los comentarios

	#Borrar los espacios entre los separadores, para poder parsear mas facil
	separators = "".join(map(lambda x : re.escape(x), ['(',')','[',']','{','}','<','>',':']))
	#El \S{,2} es un hack choto para que borre los costados izquierdos de las aserciones, en teoria anda
	#pero sospechar mucho MUCHO de el :D
	regex = re.compile("\s*(\S{,2}[" + separators + "])\s*")
	return re.sub(regex,lambda m: m.group(1), text)

def main():
	parser = argparse.ArgumentParser(description='Parsea la gramatica de arboles que definimos a JSON.')

	parser.add_argument('-i', dest='input_file', default='-', help=' Archivo con la entrada. Si no se especifica se toma entrada estandar ')
	parser.add_argument('-o', dest='output_file', default='--', help=' Archivo de salida. Si no se especifica se toma salida estandar ')

	args = parser.parse_args()

	try:
		input_file = sys.stdin if args.input_file == '-' else open(args.input_file,'r')
	except IOError as error:
		print "Error %s: %s" % error

	try:
		output_file = sys.stdout if args.output_file == '--' else open(args.output_file,'w')
	except IOError as error:
		print "Error %s: %s" % error

	cleaned = cleanup ( input_file.read() )
	data,rem = parse( cleanup( cleaned ) )

	output_file.write(json.dumps(data, sort_keys=True, indent=4))

if __name__ == "__main__":
	main()