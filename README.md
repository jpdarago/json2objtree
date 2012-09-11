json2objtree
============

Script de python para pasar de un archivo JSON a un arbol de objetivos como los que se usan en la materia 
Ingeniería de Software I de la carrera de Ciencias de la Computación en la Universidad de Buenos Aires. 

El formato de salida por ahora es SVG.

Uso
---

La idea del sistema es usarlo bajo distribuciones Linux. Es necesario tener la libreria GraphViz y la libreria
pydot. Si no se disponen de ellas y se esta corriendo con Ubuntu y privilegios de root, se puede utilizar el 
install.sh para meter todo junto.

Hay dos scripts, draw.py y parse.py. parse.py parsea de la gramatica nuestra propia a un JSON, y draw.py dibuja
tomando de entrada un .json y devolviendo en alguno de muchos formatos, como por ejemplo

* jpg
* png
* svg
* dot (Que se puede importar a yEd usando dotoxml, http://www.mydarc.de/dl9obn/programming/python/dottoxml/ )

Ambos scripts tienen ayuda de linea de comandos asi que pueden fijarse ahi, y cualquier cosa avisan.